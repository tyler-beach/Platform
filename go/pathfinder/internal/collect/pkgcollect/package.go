package pkgcollect

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/evidence"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/predicates"
)

const (
	PackageSchema = "pathfinder-evidence-package-v1"
	CollectorID   = "structured_package"
)

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

// CollectObservations validates observations against the predicate registry and
// normalizes them; never synthesizes missing ones.
func CollectObservations(packageObj map[string]any, reg *predicates.Registry) ([]map[string]any, error) {
	artifacts, err := indexArtifacts(packageObj)
	if err != nil {
		return nil, err
	}

	observationsIn, exists := packageObj["observations"]
	if !exists || observationsIn == nil {
		return []map[string]any{}, nil
	}
	list, ok := observationsIn.([]any)
	if !ok {
		return nil, &Error{Msg: "observations must be a list"}
	}
	for index, raw := range list {
		if err := validateRegistryObservation(raw, index, reg); err != nil {
			return nil, err
		}
	}
	normalized, err := evidence.NormalizeObservations(list, artifacts)
	if err != nil {
		if pe, ok := err.(*evidence.Error); ok {
			return nil, &Error{Msg: pe.Msg}
		}
		return nil, err
	}
	for _, obs := range normalized {
		obs["collector"] = CollectorID
	}
	return normalized, nil
}

func indexArtifacts(packageObj map[string]any) (map[string]map[string]any, error) {
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
		path := "tech_spec"
		if nonemptyString(block["path"]) {
			path = block["path"].(string)
		}
		rev := "sha256:" + digest
		if nonemptyString(block["revision"]) {
			rev = block["revision"].(string)
		}
		artifacts[id] = map[string]any{"sha256": digest, "path": path, "revision": rev}
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
		path := id
		if nonemptyString(block["path"]) {
			path = block["path"].(string)
		}
		rev := "sha256:" + digest
		if nonemptyString(block["revision"]) {
			rev = block["revision"].(string)
		}
		artifacts[id] = map[string]any{"sha256": digest, "path": path, "revision": rev}
	}
	return artifacts, nil
}

func validateRegistryObservation(raw any, index int, reg *predicates.Registry) error {
	item, ok := raw.(map[string]any)
	if !ok {
		return &Error{Msg: fmt.Sprintf("observations[%d] must be an object", index)}
	}
	if !nonemptyString(item["predicate"]) {
		return &Error{Msg: fmt.Sprintf("observations[%d].predicate must be a non-empty string", index)}
	}
	pred := item["predicate"].(string)
	meta, err := reg.Get(pred)
	if err != nil {
		return &Error{Msg: err.Error()}
	}
	collectors, err := reg.CollectorsFor(pred)
	if err != nil {
		return &Error{Msg: err.Error()}
	}
	allowed := false
	for _, c := range collectors {
		if c == CollectorID {
			allowed = true
			break
		}
	}
	if !allowed {
		return &Error{Msg: fmt.Sprintf("observations[%d] predicate %q is not collectable via %s", index, pred, CollectorID)}
	}
	value := item["value"]
	switch meta.ValueType {
	case "number":
		if !isNumber(value) {
			return &Error{Msg: fmt.Sprintf("observations[%d] expected number", index)}
		}
	case "boolean":
		if _, ok := value.(bool); !ok {
			return &Error{Msg: fmt.Sprintf("observations[%d] expected boolean", index)}
		}
	case "string":
		if !nonemptyString(value) {
			return &Error{Msg: fmt.Sprintf("observations[%d] expected string", index)}
		}
	}
	return nil
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
