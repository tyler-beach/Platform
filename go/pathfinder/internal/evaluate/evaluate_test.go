package evaluate_test

import (
	"encoding/json"
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
	if a["schema_version"] != "pathfinder-package-evaluation-v1" {
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
