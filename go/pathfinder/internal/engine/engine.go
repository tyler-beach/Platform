package engine

import (
	"fmt"
	"regexp"
	"sort"
	"strings"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/canonical"
)

const (
	EngineVersion       = "generic-requirement-engine-v3"
	ResultSchemaVersion = "adr-requirement-result-v1"
)

var (
	kinds = map[string]struct{}{
		"numeric_max":          {},
		"numeric_min":          {},
		"resource_present":     {},
		"boolean_required":     {},
		"set_membership":       {},
		"dependency_forbidden": {},
	}
	sha256Re = regexp.MustCompile(`^[0-9a-f]{64}$`)
)

// Evaluate applies a typed requirement against normalized observations.
// It never branches on ADR identifiers—only on kind and observation values.
func Evaluate(requirement map[string]any, observations []any, adrStatus string, scopeMatch bool) (map[string]any, error) {
	kind, err := validateRequirement(requirement)
	if err != nil {
		return nil, err
	}
	if strings.TrimSpace(adrStatus) == "" {
		return nil, fmt.Errorf("ADR status and scope_match are required and typed")
	}

	evidenceByID := map[string]map[string]any{}
	for index, raw := range observations {
		item, ok := raw.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("observations[%d] must be an object", index)
		}
		for _, field := range []string{"evidence_id", "predicate", "subject", "artifact_id", "revision", "path"} {
			if !nonemptyString(item[field]) {
				return nil, fmt.Errorf("observations[%d].%s must be a non-empty string", index, field)
			}
		}
		id := item["evidence_id"].(string)
		if _, exists := evidenceByID[id]; exists {
			return nil, fmt.Errorf("evidence IDs must be unique")
		}
		if !sha256Re.MatchString(fmt.Sprint(item["source_sha256"])) {
			return nil, fmt.Errorf("observations[%d].source_sha256 must be a lowercase SHA-256 digest", index)
		}
		locator, ok := item["locator"].(map[string]any)
		if !ok || !nonemptyString(locator["kind"]) {
			return nil, fmt.Errorf("observations[%d].locator must be typed", index)
		}
		evidenceByID[id] = item
	}

	applicable := adrStatus == "accepted" && scopeMatch
	pred := requirement["predicate"].(string)
	subject := requirement["subject"].(string)

	var matching []map[string]any
	for _, item := range evidenceByID {
		if item["predicate"] == pred && item["subject"] == subject {
			matching = append(matching, item)
		}
	}
	sort.Slice(matching, func(i, j int) bool {
		return matching[i]["evidence_id"].(string) < matching[j]["evidence_id"].(string)
	})

	var (
		outcome, relationship, rationale string
		acceptedIDs, rejectedIDs         []string
		uncertainty                      []string
	)
	acceptedIDs = []string{}
	rejectedIDs = []string{}
	uncertainty = []string{}

	if !applicable {
		outcome, relationship = "not_applicable", "not_applicable"
		rationale = "The ADR is not applicable; no compliance conclusion is asserted."
		matching = nil
	} else if len(matching) == 0 {
		outcome, relationship = "inconclusive", "insufficient_evidence"
		rationale = "No matching, provenance-bound observation was supplied."
		uncertainty = []string{"missing_observation"}
	} else {
		values := make([]any, len(matching))
		validFlags := make([]bool, len(matching))
		for i, item := range matching {
			values[i] = item["value"]
			validFlags[i] = valueValid(kind, values[i])
		}
		allValid := true
		for _, ok := range validFlags {
			if !ok {
				allValid = false
				break
			}
		}
		if !allValid {
			outcome, relationship = "inconclusive", "invalid_observation"
			rationale = "At least one matching observation has an invalid value type or range."
			for i, item := range matching {
				if !validFlags[i] {
					rejectedIDs = append(rejectedIDs, item["evidence_id"].(string))
				}
			}
			uncertainty = []string{"invalid_observation"}
		} else {
			conflict := false
			for i := 1; i < len(values); i++ {
				if !valuesEqual(values[i], values[0]) {
					conflict = true
					break
				}
			}
			if conflict {
				outcome, relationship = "inconclusive", "conflicting_evidence"
				rationale = "Matching observations disagree; no single compliance conclusion is asserted."
				uncertainty = []string{"conflicting_observations"}
			} else {
				for _, item := range matching {
					acceptedIDs = append(acceptedIDs, item["evidence_id"].(string))
				}
				value := values[0]
				if deviates(kind, requirement, value) {
					outcome, relationship = "supported_deviation", "contradicts"
					rationale = "The normalized observation violates the typed requirement."
				} else {
					outcome, relationship = "no_deviation_found", "consistent_with"
					rationale = "The normalized observation satisfies the typed requirement."
				}
			}
		}
	}

	considered := make([]string, 0, len(matching))
	provenance := make([]map[string]any, 0, len(matching))
	for _, item := range matching {
		considered = append(considered, item["evidence_id"].(string))
		prov := map[string]any{}
		for _, key := range []string{"evidence_id", "artifact_id", "revision", "path", "source_sha256", "locator"} {
			prov[key] = item[key]
		}
		provenance = append(provenance, prov)
	}

	reqCopy := map[string]any{}
	for k, v := range requirement {
		reqCopy[k] = v
	}

	result := map[string]any{
		"schema_version":          ResultSchemaVersion,
		"engine_version":          EngineVersion,
		"requirement":             reqCopy,
		"applicability":           map[string]any{"applicable": applicable, "adr_status": adrStatus, "scope_match": scopeMatch},
		"outcome":                 outcome,
		"relationship":            relationship,
		"rationale":               rationale,
		"considered_evidence_ids": considered,
		"accepted_evidence_ids":   acceptedIDs,
		"rejected_evidence_ids":   rejectedIDs,
		"uncertainty":             uncertainty,
		"provenance":              provenance,
	}
	fp, err := canonical.Fingerprint(result)
	if err != nil {
		return nil, err
	}
	result["result_sha256"] = fp
	return result, nil
}

func validateRequirement(requirement map[string]any) (string, error) {
	if requirement == nil {
		return "", fmt.Errorf("requirement must be an object")
	}
	for _, field := range []string{"requirement_id", "kind", "predicate", "subject"} {
		if !nonemptyString(requirement[field]) {
			return "", fmt.Errorf("requirement.%s must be a non-empty string", field)
		}
	}
	kind := requirement["kind"].(string)
	if _, ok := kinds[kind]; !ok {
		return "", fmt.Errorf("unsupported requirement kind")
	}
	switch kind {
	case "numeric_max", "numeric_min":
		limit, ok := asFloat(requirement["limit"])
		if !ok || limit < 0 {
			return "", fmt.Errorf("%s requires a non-negative numeric limit", kind)
		}
	case "resource_present", "boolean_required", "dependency_forbidden":
		if _, has := requirement["limit"]; has {
			return "", fmt.Errorf("%s does not accept a limit", kind)
		}
	case "set_membership":
		approved, ok := requirement["approved_set"].([]any)
		if !ok || len(approved) == 0 {
			return "", fmt.Errorf("set_membership requires a non-empty approved_set of strings")
		}
		for _, item := range approved {
			if !nonemptyString(item) {
				return "", fmt.Errorf("set_membership requires a non-empty approved_set of strings")
			}
		}
		if _, has := requirement["limit"]; has {
			return "", fmt.Errorf("set_membership does not accept a limit")
		}
	}
	return kind, nil
}

func valueValid(kind string, value any) bool {
	switch kind {
	case "numeric_max", "numeric_min":
		n, ok := asFloat(value)
		return ok && n >= 0
	case "resource_present", "boolean_required", "dependency_forbidden":
		_, ok := value.(bool)
		return ok
	case "set_membership":
		return nonemptyString(value)
	default:
		return false
	}
}

func deviates(kind string, requirement map[string]any, value any) bool {
	switch kind {
	case "numeric_max":
		n, _ := asFloat(value)
		limit, _ := asFloat(requirement["limit"])
		return n > limit
	case "numeric_min":
		n, _ := asFloat(value)
		limit, _ := asFloat(requirement["limit"])
		return n < limit
	case "resource_present", "boolean_required":
		return value == false
	case "dependency_forbidden":
		return value == true
	case "set_membership":
		approved := requirement["approved_set"].([]any)
		s := strings.TrimSpace(fmt.Sprint(value))
		for _, item := range approved {
			if item == s {
				return false
			}
		}
		return true
	default:
		panic("unsupported requirement kind")
	}
}

func nonemptyString(v any) bool {
	s, ok := v.(string)
	return ok && strings.TrimSpace(s) != ""
}

func asFloat(v any) (float64, bool) {
	switch n := v.(type) {
	case bool:
		return 0, false
	case int:
		return float64(n), true
	case int64:
		return float64(n), true
	case float64:
		return n, true
	case float32:
		return float64(n), true
	default:
		return 0, false
	}
}

func valuesEqual(a, b any) bool {
	af, aok := asFloat(a)
	bf, bok := asFloat(b)
	if aok && bok {
		return af == bf
	}
	return a == b
}
