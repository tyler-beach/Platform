package evidence

import (
	"testing"
)

func sampleSHA() string {
	return "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}

func baseObs(id, pred, subject string, value any, locator map[string]any) map[string]any {
	return map[string]any{
		"evidence_id":   id,
		"predicate":     pred,
		"subject":       subject,
		"value":         value,
		"artifact_id":   "tech_spec",
		"revision":      "sha256:" + sampleSHA(),
		"path":          "tech_spec.md",
		"source_sha256": sampleSHA(),
		"locator":       locator,
	}
}

func TestLocatorPrecisionExactSpan(t *testing.T) {
	got := LocatorPrecision(map[string]any{
		"kind":           "paste_span",
		"line":           3,
		"start":          10,
		"end":            20,
		"excerpt_sha256": sampleSHA(),
	})
	if got != PrecisionExact {
		t.Fatalf("precision=%s want EXACT", got)
	}
}

func TestLocatorPrecisionApproximateSymbolic(t *testing.T) {
	got := LocatorPrecision(map[string]any{
		"kind":  "yaml_resource",
		"value": "PodDisruptionBudget/payments",
	})
	if got != PrecisionApproximate {
		t.Fatalf("precision=%s want APPROXIMATE", got)
	}
}

func TestLocatorPrecisionUnavailableKindOnly(t *testing.T) {
	got := LocatorPrecision(map[string]any{"kind": "unknown"})
	if got != PrecisionUnavailable {
		t.Fatalf("precision=%s want UNAVAILABLE", got)
	}
}

func TestNormalizeSortStableAndAddsPrecision(t *testing.T) {
	raw := []any{
		baseObs("z-2", "session.ttl_seconds", "auth", 3600.0, map[string]any{
			"kind": "issue_claim", "value": "session.ttl_seconds",
		}),
		baseObs("a-1", "session.ttl_seconds", "auth", 3600.0, map[string]any{
			"kind": "paste_span", "line": 1, "start": 0, "end": 4, "excerpt_sha256": sampleSHA(),
		}),
	}
	// reverse again via second call with swapped order
	out, err := NormalizeObservations(raw, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 2 {
		t.Fatalf("len=%d", len(out))
	}
	if out[0]["evidence_id"] != "a-1" || out[1]["evidence_id"] != "z-2" {
		t.Fatalf("order=%v,%v", out[0]["evidence_id"], out[1]["evidence_id"])
	}
	if out[0]["locator_precision"] != PrecisionExact {
		t.Fatalf("first precision=%v", out[0]["locator_precision"])
	}
	if out[1]["locator_precision"] != PrecisionApproximate {
		t.Fatalf("second precision=%v", out[1]["locator_precision"])
	}
	if out[0]["normalizer_version"] != NormalizerVersion {
		t.Fatalf("normalizer_version=%v", out[0]["normalizer_version"])
	}

	swapped := []any{raw[1], raw[0]}
	out2, err := NormalizeObservations(swapped, nil)
	if err != nil {
		t.Fatal(err)
	}
	if out2[0]["evidence_id"] != out[0]["evidence_id"] || out2[1]["evidence_id"] != out[1]["evidence_id"] {
		t.Fatal("canonical order changed with input shuffle")
	}
}

func TestNormalizeMissingFieldFails(t *testing.T) {
	raw := []any{
		map[string]any{
			"evidence_id": "e1",
			"predicate":   "session.ttl_seconds",
			"value":       1,
			"locator":     map[string]any{"kind": "issue_claim", "value": "x"},
		},
	}
	if _, err := NormalizeObservations(raw, nil); err == nil {
		t.Fatal("expected validation error")
	}
}

func TestNormalizeBindsDigestFromArtifact(t *testing.T) {
	obs := baseObs("e1", "session.ttl_seconds", "auth", 30.0, map[string]any{
		"kind": "issue_claim", "value": "ttl",
	})
	delete(obs, "source_sha256")
	arts := map[string]map[string]any{
		"tech_spec": {"sha256": sampleSHA(), "path": "tech_spec.md", "revision": "sha256:" + sampleSHA()},
	}
	out, err := NormalizeObservations([]any{obs}, arts)
	if err != nil {
		t.Fatal(err)
	}
	if out[0]["source_sha256"] != sampleSHA() {
		t.Fatalf("source_sha256=%v", out[0]["source_sha256"])
	}
}

func TestClassifyConflicts(t *testing.T) {
	obs := []map[string]any{
		baseObs("e1", "session.ttl_seconds", "auth", 3600.0, map[string]any{"kind": "issue_claim", "value": "a"}),
		baseObs("e2", "session.ttl_seconds", "auth", 7200.0, map[string]any{"kind": "issue_claim", "value": "b"}),
		baseObs("e3", "session.ttl_seconds", "auth", 3600.0, map[string]any{"kind": "issue_claim", "value": "c"}), // still conflict set
	}
	// Fix e3 to agree with e1 for the agree case separately
	conflicts := ClassifyConflicts(obs[:2])
	if len(conflicts) != 1 {
		t.Fatalf("conflicts=%d want 1", len(conflicts))
	}
	if conflicts[0].Predicate != "session.ttl_seconds" || conflicts[0].Subject != "auth" {
		t.Fatalf("group=%+v", conflicts[0])
	}
	agree := []map[string]any{
		baseObs("e1", "session.ttl_seconds", "auth", 3600.0, map[string]any{"kind": "issue_claim", "value": "a"}),
		baseObs("e2", "session.ttl_seconds", "auth", 3600.0, map[string]any{"kind": "issue_claim", "value": "b"}),
	}
	if got := ClassifyConflicts(agree); len(got) != 0 {
		t.Fatalf("unexpected conflicts: %+v", got)
	}
}
