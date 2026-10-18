package engine_test

import (
	"crypto/sha256"
	"encoding/hex"
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/engine"
)

func obs(value any, opts ...func(map[string]any)) map[string]any {
	sum := sha256.Sum256([]byte("pinned source fixture"))
	item := map[string]any{
		"evidence_id":   "EV-1",
		"predicate":     "kubernetes.pod_disruption_budget.present",
		"subject":       "payments",
		"value":         value,
		"artifact_id":   "repo:platform",
		"revision":      "git:0123456789abcdef",
		"path":          "deploy/k8s/pdb.yaml",
		"source_sha256": hex.EncodeToString(sum[:]),
		"locator":       map[string]any{"kind": "yaml_resource", "value": "PodDisruptionBudget/payments"},
	}
	for _, opt := range opts {
		opt(item)
	}
	return item
}

func withID(id string) func(map[string]any) {
	return func(m map[string]any) { m["evidence_id"] = id }
}

func withPred(pred, subject string) func(map[string]any) {
	return func(m map[string]any) {
		m["predicate"] = pred
		m["subject"] = subject
	}
}

func TestPDBPresentAligned(t *testing.T) {
	req := map[string]any{
		"requirement_id": "ADR-PDB-001",
		"kind":           "resource_present",
		"predicate":      "kubernetes.pod_disruption_budget.present",
		"subject":        "payments",
	}
	result, err := engine.Evaluate(req, []any{obs(true)}, "accepted", true)
	if err != nil {
		t.Fatal(err)
	}
	if result["outcome"] != "no_deviation_found" {
		t.Fatalf("outcome=%v", result["outcome"])
	}
}

func TestPDBMissingDeviation(t *testing.T) {
	req := map[string]any{
		"requirement_id": "ADR-PDB-001",
		"kind":           "resource_present",
		"predicate":      "kubernetes.pod_disruption_budget.present",
		"subject":        "payments",
	}
	result, err := engine.Evaluate(req, []any{obs(false)}, "accepted", true)
	if err != nil {
		t.Fatal(err)
	}
	if result["outcome"] != "supported_deviation" || result["relationship"] != "contradicts" {
		t.Fatalf("got outcome=%v relationship=%v", result["outcome"], result["relationship"])
	}
}

func TestTTLNumericMaxDeviation(t *testing.T) {
	req := map[string]any{
		"requirement_id": "ADR-TTL-001",
		"kind":           "numeric_max",
		"predicate":      "session.ttl_seconds",
		"subject":        "web-session",
		"limit":          600,
	}
	result, err := engine.Evaluate(req, []any{obs(601, withPred("session.ttl_seconds", "web-session"))}, "accepted", true)
	if err != nil {
		t.Fatal(err)
	}
	if result["outcome"] != "supported_deviation" {
		t.Fatalf("outcome=%v", result["outcome"])
	}
}

func TestMissingObservationInconclusive(t *testing.T) {
	req := map[string]any{
		"requirement_id": "ADR-PDB-001",
		"kind":           "resource_present",
		"predicate":      "kubernetes.pod_disruption_budget.present",
		"subject":        "payments",
	}
	result, err := engine.Evaluate(req, []any{}, "accepted", true)
	if err != nil {
		t.Fatal(err)
	}
	if result["outcome"] != "inconclusive" || result["relationship"] != "insufficient_evidence" {
		t.Fatalf("got %v %v", result["outcome"], result["relationship"])
	}
}

func TestConflictingObservationsInconclusive(t *testing.T) {
	req := map[string]any{
		"requirement_id": "ADR-PDB-001",
		"kind":           "resource_present",
		"predicate":      "kubernetes.pod_disruption_budget.present",
		"subject":        "payments",
	}
	result, err := engine.Evaluate(req, []any{obs(true), obs(false, withID("EV-2"))}, "accepted", true)
	if err != nil {
		t.Fatal(err)
	}
	if result["outcome"] != "inconclusive" || result["relationship"] != "conflicting_evidence" {
		t.Fatalf("got %v %v", result["outcome"], result["relationship"])
	}
}

func TestOutOfScopeNotApplicable(t *testing.T) {
	req := map[string]any{
		"requirement_id": "ADR-PDB-001",
		"kind":           "resource_present",
		"predicate":      "kubernetes.pod_disruption_budget.present",
		"subject":        "payments",
	}
	result, err := engine.Evaluate(req, []any{obs(false)}, "accepted", false)
	if err != nil {
		t.Fatal(err)
	}
	if result["outcome"] != "not_applicable" {
		t.Fatalf("outcome=%v", result["outcome"])
	}
	ids, _ := result["considered_evidence_ids"].([]string)
	if len(ids) != 0 {
		t.Fatalf("expected empty considered, got %v", ids)
	}
}

func TestDuplicateEvidenceIDsRejected(t *testing.T) {
	req := map[string]any{
		"requirement_id": "ADR-PDB-001",
		"kind":           "resource_present",
		"predicate":      "kubernetes.pod_disruption_budget.present",
		"subject":        "payments",
	}
	_, err := engine.Evaluate(req, []any{obs(true), obs(false)}, "accepted", true)
	if err == nil {
		t.Fatal("expected error")
	}
}

func TestNumericBooleanInvalidObservation(t *testing.T) {
	req := map[string]any{
		"requirement_id": "ADR-TTL-001",
		"kind":           "numeric_max",
		"predicate":      "session.ttl_seconds",
		"subject":        "web-session",
		"limit":          600,
	}
	result, err := engine.Evaluate(req, []any{obs(true, withPred("session.ttl_seconds", "web-session"))}, "accepted", true)
	if err != nil {
		t.Fatal(err)
	}
	if result["outcome"] != "inconclusive" || result["relationship"] != "invalid_observation" {
		t.Fatalf("got %v %v", result["outcome"], result["relationship"])
	}
}

func TestStableResultFingerprint(t *testing.T) {
	req := map[string]any{
		"requirement_id": "ADR-PDB-001",
		"kind":           "resource_present",
		"predicate":      "kubernetes.pod_disruption_budget.present",
		"subject":        "payments",
	}
	a, err := engine.Evaluate(req, []any{obs(true)}, "accepted", true)
	if err != nil {
		t.Fatal(err)
	}
	b, err := engine.Evaluate(req, []any{obs(true)}, "accepted", true)
	if err != nil {
		t.Fatal(err)
	}
	if a["result_sha256"] != b["result_sha256"] {
		t.Fatalf("fingerprint drift: %v vs %v", a["result_sha256"], b["result_sha256"])
	}
}
