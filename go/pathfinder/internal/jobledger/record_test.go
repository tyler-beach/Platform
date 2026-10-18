package jobledger_test

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/jobledger"
)

func TestBuildAndWriteLeanRecord(t *testing.T) {
	pkg := map[string]any{"package_id": "github-issue-1", "schema_version": "pathfinder-evidence-package-v1"}
	report := map[string]any{
		"aggregate_status": "mixed",
		"report_sha256":    "abc",
		"engine_version":   "generic-requirement-engine-v3",
	}
	rec, err := jobledger.Build(1, "o/r", "99", "1", "generic-requirement-engine-v3", pkg, report, nil)
	if err != nil {
		t.Fatal(err)
	}
	if rec.JobID == "" || rec.PackageSHA256 == "" || !rec.OK {
		t.Fatalf("incomplete record: %+v", rec)
	}
	dir := t.TempDir()
	path := filepath.Join(dir, "job.json")
	if err := jobledger.WriteFile(path, rec); err != nil {
		t.Fatal(err)
	}
	raw, _ := os.ReadFile(path)
	var decoded map[string]any
	if err := json.Unmarshal(raw, &decoded); err != nil {
		t.Fatal(err)
	}
	if decoded["schema_version"] != jobledger.SchemaVersion {
		t.Fatalf("schema=%v", decoded["schema_version"])
	}
	encoded := string(raw)
	if len(encoded) > 0 && encoded[len(encoded)-1] != '\n' {
		t.Fatal("expected trailing newline for JSONL append")
	}
}
