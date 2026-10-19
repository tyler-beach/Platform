// Package evidence provides pure normalization for Pathfinder observations.
package evidence

import (
	"fmt"
	"sort"
	"strings"
)

const (
	NormalizerVersion = "evidence-normalize-v1"

	PrecisionExact       = "EXACT"
	PrecisionApproximate = "APPROXIMATE"
	PrecisionUnavailable = "UNAVAILABLE"
)

// Error is a domain validation failure during normalize.
type Error struct{ Msg string }

func (e *Error) Error() string { return e.Msg }

// ConflictGroup is a predicate+subject set whose observation values disagree.
type ConflictGroup struct {
	Predicate   string
	Subject     string
	EvidenceIDs []string
}

// NormalizeObservations validates raw observations, binds digests when absent,
// derives locator_precision, and returns a newly allocated canonically sorted list.
// It never invents observations. registry may be nil only in unit tests that
// pre-validate value types; production collect always supplies checks first.
func NormalizeObservations(raw []any, artifacts map[string]map[string]any) ([]map[string]any, error) {
	if raw == nil {
		return []map[string]any{}, nil
	}
	seen := map[string]struct{}{}
	out := make([]map[string]any, 0, len(raw))
	for index, item := range raw {
		obs, err := normalizeOne(item, index, artifacts)
		if err != nil {
			return nil, err
		}
		id := obs["evidence_id"].(string)
		if _, dup := seen[id]; dup {
			return nil, &Error{Msg: "observation evidence_ids must be unique"}
		}
		seen[id] = struct{}{}
		out = append(out, obs)
	}
	SortObservations(out)
	return out, nil
}

// SortObservations orders by predicate, subject, artifact_id, path, evidence_id.
func SortObservations(observations []map[string]any) {
	sort.SliceStable(observations, func(i, j int) bool {
		a, b := observations[i], observations[j]
		for _, key := range []string{"predicate", "subject", "artifact_id", "path", "evidence_id"} {
			as := fmt.Sprint(a[key])
			bs := fmt.Sprint(b[key])
			if as != bs {
				return as < bs
			}
		}
		return false
	})
}

// ClassifyConflicts reports predicate+subject groups with unequal values.
func ClassifyConflicts(observations []map[string]any) []ConflictGroup {
	type key struct{ pred, subject string }
	type bucket struct {
		ids    []string
		values []any
	}
	groups := map[key]*bucket{}
	order := []key{}
	for _, obs := range observations {
		pred, _ := obs["predicate"].(string)
		subject, _ := obs["subject"].(string)
		id, _ := obs["evidence_id"].(string)
		k := key{pred, subject}
		b, ok := groups[k]
		if !ok {
			b = &bucket{}
			groups[k] = b
			order = append(order, k)
		}
		b.ids = append(b.ids, id)
		b.values = append(b.values, obs["value"])
	}
	var conflicts []ConflictGroup
	for _, k := range order {
		b := groups[k]
		if len(b.values) < 2 {
			continue
		}
		conflict := false
		for i := 1; i < len(b.values); i++ {
			if !valuesEqual(b.values[i], b.values[0]) {
				conflict = true
				break
			}
		}
		if conflict {
			ids := append([]string(nil), b.ids...)
			sort.Strings(ids)
			conflicts = append(conflicts, ConflictGroup{
				Predicate:   k.pred,
				Subject:     k.subject,
				EvidenceIDs: ids,
			})
		}
	}
	return conflicts
}

// LocatorPrecision derives EXACT / APPROXIMATE / UNAVAILABLE from a locator map.
func LocatorPrecision(locator map[string]any) string {
	if locator == nil || !nonemptyString(locator["kind"]) {
		return PrecisionUnavailable
	}
	if hasSpan(locator) || nonemptyString(locator["excerpt_sha256"]) {
		return PrecisionExact
	}
	if nonemptyString(locator["value"]) {
		return PrecisionApproximate
	}
	return PrecisionUnavailable
}

func normalizeOne(raw any, index int, artifacts map[string]map[string]any) (map[string]any, error) {
	item, ok := raw.(map[string]any)
	if !ok {
		return nil, &Error{Msg: fmt.Sprintf("observations[%d] must be an object", index)}
	}
	for _, field := range []string{"evidence_id", "predicate", "subject", "artifact_id", "revision", "path"} {
		if !nonemptyString(item[field]) {
			return nil, &Error{Msg: fmt.Sprintf("observations[%d].%s must be a non-empty string", index, field)}
		}
	}
	locator, ok := item["locator"].(map[string]any)
	if !ok || !nonemptyString(locator["kind"]) {
		return nil, &Error{Msg: fmt.Sprintf("observations[%d].locator must be typed", index)}
	}
	if item["value"] == nil {
		return nil, &Error{Msg: fmt.Sprintf("observations[%d].value is required", index)}
	}
	sourceSHA := strings.TrimSpace(fmt.Sprint(item["source_sha256"]))
	if !sha256Hex(sourceSHA) {
		art := artifacts[item["artifact_id"].(string)]
		if art == nil || !nonemptyString(art["sha256"]) {
			return nil, &Error{Msg: fmt.Sprintf("observations[%d] missing source_sha256 and unknown artifact_id", index)}
		}
		sourceSHA = art["sha256"].(string)
	}
	precision := LocatorPrecision(locator)
	collector := item["collector"]
	if !nonemptyString(collector) {
		collector = "structured_package"
	}
	return map[string]any{
		"evidence_id":         item["evidence_id"],
		"predicate":           item["predicate"],
		"subject":             item["subject"],
		"value":               item["value"],
		"artifact_id":         item["artifact_id"],
		"revision":            item["revision"],
		"path":                item["path"],
		"source_sha256":       sourceSHA,
		"locator":             cloneLocator(locator),
		"collector":           collector,
		"locator_precision":   precision,
		"normalizer_version":  NormalizerVersion,
	}, nil
}

func hasSpan(locator map[string]any) bool {
	if line, ok := asInt(locator["line"]); ok && line >= 1 {
		return true
	}
	if start, ok := asInt(locator["start_line"]); ok && start >= 1 {
		end, endOK := asInt(locator["end_line"])
		return !endOK || end >= start
	}
	start, sok := asInt(locator["start"])
	end, eok := asInt(locator["end"])
	return sok && eok && start >= 0 && end >= start
}

func asInt(v any) (int, bool) {
	switch n := v.(type) {
	case int:
		return n, true
	case int64:
		return int(n), true
	case float64:
		if n == float64(int(n)) {
			return int(n), true
		}
	}
	return 0, false
}

func nonemptyString(v any) bool {
	s, ok := v.(string)
	return ok && strings.TrimSpace(s) != ""
}

func sha256Hex(s string) bool {
	if len(s) != 64 {
		return false
	}
	for _, c := range s {
		if (c < '0' || c > '9') && (c < 'a' || c > 'f') {
			return false
		}
	}
	return true
}

func cloneLocator(locator map[string]any) map[string]any {
	out := make(map[string]any, len(locator))
	for k, v := range locator {
		out[k] = v
	}
	return out
}

func valuesEqual(a, b any) bool {
	switch av := a.(type) {
	case float64:
		bv, ok := b.(float64)
		return ok && av == bv
	case bool:
		bv, ok := b.(bool)
		return ok && av == bv
	case string:
		bv, ok := b.(string)
		return ok && av == bv
	default:
		return fmt.Sprint(a) == fmt.Sprint(b)
	}
}
