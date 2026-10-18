package catalog

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/engine"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/predicates"
)

// DefaultDir returns .poc/requirement_catalog relative to a repo root.
func DefaultDir(repoRoot string) string {
	return filepath.Join(repoRoot, ".poc", "requirement_catalog")
}

// LoadRequirements loads approved rows from requirements.jsonl.
func LoadRequirements(catalogDir string, reg *predicates.Registry) ([]map[string]any, error) {
	path := filepath.Join(catalogDir, "requirements.jsonl")
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	kinds := map[string]struct{}{
		"numeric_max": {}, "numeric_min": {}, "resource_present": {},
		"boolean_required": {}, "set_membership": {}, "dependency_forbidden": {},
	}
	var rows []map[string]any
	seen := map[string]struct{}{}
	scanner := bufio.NewScanner(f)
	// Allow long JSONL lines.
	buf := make([]byte, 0, 64*1024)
	scanner.Buffer(buf, 1024*1024)
	lineNo := 0
	for scanner.Scan() {
		lineNo++
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var item map[string]any
		if err := json.Unmarshal([]byte(line), &item); err != nil {
			return nil, fmt.Errorf("requirements.jsonl:%d: %w", lineNo, err)
		}
		if item["approval_state"] != "approved" {
			return nil, fmt.Errorf("requirements.jsonl:%d is not approved", lineNo)
		}
		kind, _ := item["kind"].(string)
		if _, ok := kinds[kind]; !ok {
			return nil, fmt.Errorf("requirements.jsonl:%d unsupported kind %q", lineNo, kind)
		}
		pred, _ := item["predicate"].(string)
		if err := reg.AssertsCompatible(kind, pred); err != nil {
			return nil, fmt.Errorf("requirements.jsonl:%d: %w", lineNo, err)
		}
		id, _ := item["requirement_id"].(string)
		if id == "" {
			return nil, fmt.Errorf("requirements.jsonl:%d missing requirement_id", lineNo)
		}
		if _, dup := seen[id]; dup {
			return nil, fmt.Errorf("duplicate requirement_id in catalog")
		}
		seen[id] = struct{}{}
		rows = append(rows, item)
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	_ = engine.EngineVersion // keep engine linkage explicit for versioning docs
	return rows, nil
}

// RequirementForEngine projects a catalog row into an engine requirement.
func RequirementForEngine(row map[string]any) map[string]any {
	req := map[string]any{
		"requirement_id": row["requirement_id"],
		"kind":           row["kind"],
		"predicate":      row["predicate"],
		"subject":        row["subject"],
	}
	if v, ok := row["limit"]; ok {
		req["limit"] = v
	}
	if v, ok := row["approved_set"]; ok {
		req["approved_set"] = v
	}
	return req
}

// SubjectMap returns predicate → subject from catalog rows.
func SubjectMap(rows []map[string]any) map[string]string {
	out := map[string]string{}
	for _, row := range rows {
		pred, _ := row["predicate"].(string)
		subj, _ := row["subject"].(string)
		if pred != "" && subj != "" {
			out[pred] = subj
		}
	}
	return out
}
