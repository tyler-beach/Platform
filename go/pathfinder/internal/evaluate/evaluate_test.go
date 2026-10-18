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
	a, err := evaluate.EvaluatePackage(pkg, catalogDir, "accepted")
	if err != nil {
		t.Fatal(err)
	}
	b, err := evaluate.EvaluatePackage(pkg, catalogDir, "accepted")
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
}
