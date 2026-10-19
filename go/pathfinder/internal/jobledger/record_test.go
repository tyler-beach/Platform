package jobledger_test

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/jobledger"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/telemetry"
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

func TestBuildCarriesOnlyAllowlistedOutcomeCounts(t *testing.T) {
	counts := map[string]int{
		"supported_deviation": 2,
		"no_deviation_found":  3,
		"inconclusive":        4,
		"not_applicable":      1,
	}
	report := map[string]any{
		"aggregate_status": "mixed",
		"counts":           counts,
	}
	rec, err := jobledger.Build(3, "o/r", "9", "1", "engine", nil, report, nil)
	if err != nil {
		t.Fatal(err)
	}
	if rec.SchemaVersion != "pathfinder-job-record-v3" {
		t.Fatalf("schema=%q", rec.SchemaVersion)
	}
	if !reflect.DeepEqual(rec.OutcomeCounts, counts) {
		t.Fatalf("outcome counts=%v, want %v", rec.OutcomeCounts, counts)
	}

	report["counts"] = map[string]int{"supported_deviation": -1}
	if _, err := jobledger.Build(3, "o/r", "9", "1", "engine", nil, report, nil); err == nil {
		t.Fatal("expected negative count rejection")
	}
	report["counts"] = map[string]int{"issue_body": 1}
	if _, err := jobledger.Build(3, "o/r", "9", "1", "engine", nil, report, nil); err == nil {
		t.Fatal("expected unknown outcome rejection")
	}
}

func TestBuildWithTelemetryPersistsOnlyAllowlistedStageAggregates(t *testing.T) {
	stageTelemetry := map[string]telemetry.StageMetric{
		"evaluation": {Runs: 1, DurationTotalNS: 2500000, DurationMaxNS: 2500000},
	}
	rec, err := jobledger.BuildWithTelemetry(1, "o/r", "99", "1", "engine", nil, nil, nil, stageTelemetry)
	if err != nil {
		t.Fatal(err)
	}
	if rec.SchemaVersion != "pathfinder-job-record-v3" || rec.StageTelemetry["evaluation"].DurationTotalNS != 2500000 {
		t.Fatalf("telemetry not persisted: %+v", rec)
	}
	_, err = jobledger.BuildWithTelemetry(1, "o/r", "99", "1", "engine", nil, nil, nil, map[string]telemetry.StageMetric{"issue-secret": {Runs: 1}})
	if err == nil {
		t.Fatal("expected unknown telemetry stage to be rejected")
	}
}
