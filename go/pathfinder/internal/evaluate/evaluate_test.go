package evaluate_test

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/evaluate"
)

func repoRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("no caller")
	}
	// go/pathfinder/internal/evaluate -> repo root
	return filepath.Clean(filepath.Join(filepath.Dir(file), "..", "..", "..", ".."))
}

func TestEvaluateSamplePackageStable(t *testing.T) {
	root := repoRoot(t)
	catalogDir := filepath.Join(root, ".poc", "requirement_catalog")
	pkgPath := filepath.Join(catalogDir, "sample_packages", "multi-domain-session-service", "package.json")
	raw, err := os.ReadFile(pkgPath)
	if err != nil {
		t.Fatal(err)
	}
	var pkg map[string]any
	if err := json.Unmarshal(raw, &pkg); err != nil {
		t.Fatal(err)
	}
	a, err := evaluate.EvaluatePackageWithMode(pkg, catalogDir, "accepted", "synthetic")
	if err != nil {
		t.Fatal(err)
	}
	b, err := evaluate.EvaluatePackageWithMode(pkg, catalogDir, "accepted", "synthetic")
	if err != nil {
		t.Fatal(err)
	}
	if a["schema_version"] != "pathfinder-package-evaluation-v2" {
		t.Fatalf("schema=%v", a["schema_version"])
	}
	if a["report_sha256"] != b["report_sha256"] {
		t.Fatalf("report fingerprint drift")
	}
	if a["catalog_size"].(int) != 100 {
		t.Fatalf("catalog_size=%v", a["catalog_size"])
	}
	status, _ := a["aggregate_status"].(string)
	if status == "" {
		t.Fatal("missing aggregate_status")
	}
	cat, _ := a["catalog"].(map[string]any)
	if cat["mode"] != "synthetic" || cat["manifest_sha256"] == "" {
		t.Fatalf("catalog identity=%v", cat)
	}
}

func TestEvaluateRealCatalogDomainApplicability(t *testing.T) {
	root := repoRoot(t)
	catalogDir := filepath.Join(root, "data", "adr_catalog")
	pkg := map[string]any{
		"schema_version": "pathfinder-evidence-package-v1",
		"package_id":     "scope-identity-only",
		"scope":          map[string]any{"domains": []any{"identity"}},
		"observations":   []any{},
	}
	report, err := evaluate.EvaluatePackageWithMode(pkg, catalogDir, "accepted", "real")
	if err != nil {
		t.Fatal(err)
	}
	if report["catalog_size"].(int) != 200 {
		t.Fatalf("catalog_size=%v", report["catalog_size"])
	}
	inScope := report["in_scope_count"].(int)
	if inScope < 1 || inScope >= 200 {
		t.Fatalf("in_scope_count=%v want identity-only subset", inScope)
	}
	if report["aggregate_status"] == "all_aligned" {
		t.Fatal("no applicable confident outcomes should not look all_aligned")
	}
	cat, _ := report["catalog"].(map[string]any)
	if cat["mode"] != "real" || cat["catalog_id"] != "platform-real-adr-v1" {
		t.Fatalf("catalog=%v", cat)
	}
	counts, _ := report["counts"].(map[string]int)
	if counts["not_applicable"] < 100 {
		t.Fatalf("expected most non-identity rows not_applicable, counts=%v", counts)
	}
}

func TestEvaluateRealSamplePackageConfidentOutcomes(t *testing.T) {
	root := repoRoot(t)
	catalogDir := filepath.Join(root, "data", "adr_catalog")
	pkgPath := filepath.Join(catalogDir, "sample_packages", "session-and-pdb", "package.json")
	raw, err := os.ReadFile(pkgPath)
	if err != nil {
		t.Fatal(err)
	}
	var pkg map[string]any
	if err := json.Unmarshal(raw, &pkg); err != nil {
		t.Fatal(err)
	}
	report, err := evaluate.EvaluatePackage(pkg, catalogDir, "accepted")
	if err != nil {
		t.Fatal(err)
	}
	if report["observation_count"].(int) < 5 {
		t.Fatalf("observation_count=%v", report["observation_count"])
	}
	counts, _ := report["counts"].(map[string]int)
	confident := counts["supported_deviation"] + counts["no_deviation_found"]
	if confident < 1 {
		t.Fatalf("expected confident outcomes, counts=%v", counts)
	}
}

func TestEvaluateNoApplicableRequirements(t *testing.T) {
	root := repoRoot(t)
	catalogDir := filepath.Join(root, "data", "adr_catalog")
	pkg := map[string]any{
		"schema_version": "pathfinder-evidence-package-v1",
		"package_id":     "scope-unknown-domain",
		"scope":          map[string]any{"domains": []any{"hr-benefits"}},
		"observations":   []any{},
	}
	report, err := evaluate.EvaluatePackageWithMode(pkg, catalogDir, "accepted", "real")
	if err != nil {
		t.Fatal(err)
	}
	if report["aggregate_status"] != "not_applicable_only" {
		t.Fatalf("status=%v", report["aggregate_status"])
	}
	if report["in_scope_count"].(int) != 0 {
		t.Fatalf("in_scope_count=%v", report["in_scope_count"])
	}
}

func TestEvaluateCombinesEvidenceAndPreservesSourceProvenance(t *testing.T) {
	root := repoRoot(t)
	catalogDir := filepath.Join(root, "data", "adr_catalog")
	tech := "Sessions expire after 20 minutes."
	code := "const SessionTTL = 3600 // Sessions expire after 60 minutes."
	pkg := map[string]any{
		"schema_version": "pathfinder-evidence-package-v1",
		"package_id":     "combined-evidence",
		"scope":          map[string]any{"domains": []any{"identity"}},
		"tech_spec":      map[string]any{"artifact_id": "spec-1", "path": "spec.md", "revision": "r1", "content": tech},
		"code":           []any{map[string]any{"artifact_id": "code-1", "path": "session.go", "revision": "r2", "content": code}},
		"observations":   []any{},
	}
	report, err := evaluate.EvaluatePackageWithMode(pkg, catalogDir, "accepted", "real")
	if err != nil {
		t.Fatal(err)
	}
	results, _ := report["results"].([]map[string]any)
	var ttlResults []map[string]any
	for _, row := range results {
		if row["predicate"] == "session.ttl_seconds" && row["in_scope"] == true {
			ttlResults = append(ttlResults, row)
		}
	}
	if len(ttlResults) != 1 {
		t.Fatalf("expected one combined requirement result, got %d: %#v", len(ttlResults), ttlResults)
	}
	if ttlResults[0]["outcome"] != "inconclusive" || ttlResults[0]["relationship"] != "conflicting_evidence" {
		t.Fatalf("spec/code disagreement should be retained as a conflict: %#v", ttlResults[0])
	}
	provenance, _ := ttlResults[0]["provenance"].([]map[string]any)
	if len(provenance) != 2 {
		t.Fatalf("expected both sources in result provenance, got %#v", provenance)
	}
	roles := map[string]bool{}
	for _, source := range provenance {
		roles[fmt.Sprint(source["evidence_role"])] = true
	}
	if !roles["design_assertion"] || !roles["implementation_fact"] {
		t.Fatalf("combined finding lost source roles: %#v", provenance)
	}
}

func TestMatchingValuesFromDifferentSourcesSupportOneResult(t *testing.T) {
	root := repoRoot(t)
	catalogDir := filepath.Join(root, "data", "adr_catalog")
	pkg := map[string]any{
		"schema_version": "pathfinder-evidence-package-v1",
		"package_id":     "matching-evidence",
		"scope":          map[string]any{"domains": []any{"identity"}},
		"tech_spec":      map[string]any{"artifact_id": "spec-1", "path": "spec.md", "revision": "r1", "content": "Sessions expire after 10 minutes."},
		"code":           []any{map[string]any{"artifact_id": "code-1", "path": "session.go", "revision": "r2", "content": "const SessionTTL = 600 // Sessions expire after 10 minutes."}},
		"observations":   []any{},
	}
	report, err := evaluate.EvaluatePackageWithMode(pkg, catalogDir, "accepted", "real")
	if err != nil {
		t.Fatal(err)
	}
	results, _ := report["results"].([]map[string]any)
	for _, row := range results {
		if row["predicate"] != "session.ttl_seconds" || row["in_scope"] != true {
			continue
		}
		if row["outcome"] != "no_deviation_found" {
			t.Fatalf("matching in-policy evidence should support one aligned result: %#v", row)
		}
		refs, _ := row["provenance"].([]map[string]any)
		if len(refs) != 2 {
			t.Fatalf("expected both source refs on the unified result, got %#v", refs)
		}
		return
	}
	t.Fatal("no in-scope session TTL result")
}

func TestNoExtractedFactRemainsInconclusiveWithoutRoleRows(t *testing.T) {
	root := repoRoot(t)
	catalogDir := filepath.Join(root, "data", "adr_catalog")
	pkg := map[string]any{"schema_version": "pathfinder-evidence-package-v1", "package_id": "no-extracted-fact", "scope": map[string]any{"domains": []any{"identity"}}, "code": []any{map[string]any{"artifact_id": "code-1", "path": "session.go", "revision": "r2", "content": "package session\nfunc Start() {}"}}, "observations": []any{}}
	report, err := evaluate.EvaluatePackageWithMode(pkg, catalogDir, "accepted", "real")
	if err != nil {
		t.Fatal(err)
	}
	results, _ := report["results"].([]map[string]any)
	resultCount := 0
	for _, row := range results {
		if row["predicate"] == "session.ttl_seconds" && row["in_scope"] == true {
			resultCount++
			if row["outcome"] != "inconclusive" {
				t.Fatalf("missing evidence was not inconclusive: %#v", row)
			}
		}
	}
	if resultCount != 1 {
		t.Fatalf("expected one unified inconclusive result, got %d", resultCount)
	}
}

func TestEnabledSemanticExtractionWithoutCredentialsReportsFallback(t *testing.T) {
	t.Setenv("PATHFINDER_ENABLE_MODEL_EXTRACT", "true")
	t.Setenv("ANTHROPIC_API_KEY", "")
	t.Setenv("ANTHROPIC_MODEL", "")
	root := repoRoot(t)
	catalogDir := filepath.Join(root, "data", "adr_catalog")
	pkg := map[string]any{"schema_version": "pathfinder-evidence-package-v1", "package_id": "fallback", "scope": map[string]any{"domains": []any{"identity"}}, "tech_spec": map[string]any{"artifact_id": "spec-1", "path": "spec.md", "revision": "r1", "content": "Sessions expire after 20 minutes."}, "observations": []any{}}
	report, err := evaluate.EvaluatePackageWithMode(pkg, catalogDir, "accepted", "real")
	if err != nil {
		t.Fatal(err)
	}
	extraction, _ := report["extraction"].(map[string]any)
	if extraction["status"] != "unavailable_configuration" || extraction["fallback_extractor"] == nil {
		t.Fatalf("fallback status not explicit: %#v", extraction)
	}
}
