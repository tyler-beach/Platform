package pkgcollect

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"strings"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/predicates"
)

const (
	PackageSchema = "pathfinder-evidence-package-v1"
	CollectorID   = "structured_package"
)

var sha256Re = regexp.MustCompile(`^[0-9a-f]{64}$`)

type Error struct{ Msg string }

func (e *Error) Error() string { return e.Msg }

func sha256Text(content string) string {
	sum := sha256.Sum256([]byte(content))
	return hex.EncodeToString(sum[:])
}

func nonemptyString(v any) bool {
	s, ok := v.(string)
	return ok && strings.TrimSpace(s) != ""
}

// LoadPackage reads and validates schema_version.
func LoadPackage(path string) (map[string]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var packageObj map[string]any
	if err := json.Unmarshal(raw, &packageObj); err != nil {
		return nil, &Error{Msg: fmt.Sprintf("package is not valid JSON: %v", err)}
	}
	if packageObj["schema_version"] != PackageSchema {
		return nil, &Error{Msg: fmt.Sprintf("unsupported package schema_version: %v", packageObj["schema_version"])}
	}
	return packageObj, nil
}

// CollectObservations validates observations; never synthesizes missing ones.
func CollectObservations(packageObj map[string]any, reg *predicates.Registry) ([]map[string]any, error) {
	artifacts := map[string]map[string]any{}
	if block, ok := packageObj["tech_spec"].(map[string]any); ok && nonemptyString(block["content"]) {
		content := block["content"].(string)
		digest := sha256Text(content)
		if s, ok := block["sha256"].(string); ok && s != "" && s != digest {
			return nil, &Error{Msg: "tech_spec sha256 does not match content"}
		}
		if s, ok := block["sha256"].(string); ok && s != "" {
			digest = s
		}
		id := "tech_spec"
		if nonemptyString(block["artifact_id"]) {
			id = block["artifact_id"].(string)
		}
		if _, duplicate := artifacts[id]; duplicate {
			return nil, &Error{Msg: fmt.Sprintf("duplicate artifact_id %q", id)}
		}
		path := "tech_spec"
		if nonemptyString(block["path"]) {
			path = block["path"].(string)
		}
		rev := "sha256:" + digest
		if nonemptyString(block["revision"]) {
			rev = block["revision"].(string)
		}
		artifacts[id] = map[string]any{"sha256": digest, "path": path, "revision": rev, "evidence_role": "design_assertion"}
	}
	codeList, _ := packageObj["code"].([]any)
	for index, raw := range codeList {
		block, ok := raw.(map[string]any)
		if !ok || !nonemptyString(block["content"]) {
			return nil, &Error{Msg: fmt.Sprintf("code[%d] requires content", index)}
		}
		content := block["content"].(string)
		digest := sha256Text(content)
		if s, ok := block["sha256"].(string); ok && s != "" && s != digest {
			return nil, &Error{Msg: fmt.Sprintf("code[%d] sha256 does not match content", index)}
		}
		if s, ok := block["sha256"].(string); ok && s != "" {
			digest = s
		}
		id := fmt.Sprintf("code-%d", index)
		if nonemptyString(block["artifact_id"]) {
			id = block["artifact_id"].(string)
		}
		if _, duplicate := artifacts[id]; duplicate {
			return nil, &Error{Msg: fmt.Sprintf("duplicate artifact_id %q", id)}
		}
		path := id
		if nonemptyString(block["path"]) {
			path = block["path"].(string)
		}
		rev := "sha256:" + digest
		if nonemptyString(block["revision"]) {
			rev = block["revision"].(string)
		}
		artifacts[id] = map[string]any{"sha256": digest, "path": path, "revision": rev, "evidence_role": "implementation_fact"}
	}

	observationsIn, exists := packageObj["observations"]
	if !exists || observationsIn == nil {
		return []map[string]any{}, nil
	}
	list, ok := observationsIn.([]any)
	if !ok {
		return nil, &Error{Msg: "observations must be a list"}
	}
	seen := map[string]struct{}{}
	var out []map[string]any
	for index, raw := range list {
		obs, err := validateObservation(raw, index, artifacts, reg)
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
	return out, nil
}

func validateObservation(raw any, index int, artifacts map[string]map[string]any, reg *predicates.Registry) (map[string]any, error) {
	item, ok := raw.(map[string]any)
	if !ok {
		return nil, &Error{Msg: fmt.Sprintf("observations[%d] must be an object", index)}
	}
	for _, field := range []string{"evidence_id", "predicate", "subject", "artifact_id", "revision", "path"} {
		if !nonemptyString(item[field]) {
			return nil, &Error{Msg: fmt.Sprintf("observations[%d].%s must be a non-empty string", index, field)}
		}
	}
	pred := item["predicate"].(string)
	meta, err := reg.Get(pred)
	if err != nil {
		return nil, &Error{Msg: err.Error()}
	}
	collectors, err := reg.CollectorsFor(pred)
	if err != nil {
		return nil, &Error{Msg: err.Error()}
	}
	allowed := false
	for _, c := range collectors {
		if c == CollectorID {
			allowed = true
			break
		}
	}
	if !allowed {
		return nil, &Error{Msg: fmt.Sprintf("observations[%d] predicate %q is not collectable via %s", index, pred, CollectorID)}
	}
	locator, ok := item["locator"].(map[string]any)
	if !ok || !nonemptyString(locator["kind"]) {
		return nil, &Error{Msg: fmt.Sprintf("observations[%d].locator must be typed", index)}
	}
	value := item["value"]
	switch meta.ValueType {
	case "number":
		if !isNumber(value) {
			return nil, &Error{Msg: fmt.Sprintf("observations[%d] expected number", index)}
		}
	case "boolean":
		if _, ok := value.(bool); !ok {
			return nil, &Error{Msg: fmt.Sprintf("observations[%d] expected boolean", index)}
		}
	case "string":
		if !nonemptyString(value) {
			return nil, &Error{Msg: fmt.Sprintf("observations[%d] expected string", index)}
		}
	}
	sourceSHA := ""
	if rawSHA, exists := item["source_sha256"]; exists && rawSHA != nil {
		if !nonemptyString(rawSHA) || !sha256Re.MatchString(rawSHA.(string)) {
			return nil, &Error{Msg: fmt.Sprintf("observations[%d].source_sha256 must be a SHA-256 digest", index)}
		}
		sourceSHA = rawSHA.(string)
	}
	art := artifacts[item["artifact_id"].(string)]
	role := "implementation_fact"
	if art != nil {
		if !sha256Re.MatchString(sourceSHA) {
			sourceSHA = art["sha256"].(string)
		}
		if sourceSHA != art["sha256"] || item["revision"] != art["revision"] || item["path"] != art["path"] {
			return nil, &Error{Msg: fmt.Sprintf("observations[%d] provenance does not match pinned artifact", index)}
		}
		role = art["evidence_role"].(string)
	} else if !sha256Re.MatchString(sourceSHA) {
		return nil, &Error{Msg: fmt.Sprintf("observations[%d] missing source_sha256 and unknown artifact_id", index)}
	}
	if rawRole, exists := item["evidence_role"]; exists && rawRole != nil {
		suppliedRole, ok := rawRole.(string)
		if !ok || (suppliedRole != "" && suppliedRole != role) {
			return nil, &Error{Msg: fmt.Sprintf("observations[%d].evidence_role does not match pinned artifact", index)}
		}
	}
	if role != "design_assertion" && role != "implementation_fact" {
		return nil, &Error{Msg: fmt.Sprintf("observations[%d].evidence_role is invalid", index)}
	}
	return map[string]any{
		"evidence_id":   item["evidence_id"],
		"predicate":     item["predicate"],
		"subject":       item["subject"],
		"value":         value,
		"artifact_id":   item["artifact_id"],
		"revision":      item["revision"],
		"path":          item["path"],
		"source_sha256": sourceSHA,
		"evidence_role": role,
		"locator":       locator,
		"collector":     CollectorID,
	}, nil
}

func isNumber(v any) bool {
	switch v.(type) {
	case bool:
		return false
	case float64, float32, int, int64, json.Number:
		return true
	default:
		return false
	}
}
