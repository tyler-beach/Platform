package pkgcollect_test

import (
	"crypto/sha256"
	"encoding/hex"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/collect/pkgcollect"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/predicates"
)

func fixture(t *testing.T, role string, digestOverride string) map[string]any {
	t.Helper()
	content := "Sessions expire after 20 minutes."
	sum := sha256.Sum256([]byte(content))
	digest := hex.EncodeToString(sum[:])
	if digestOverride != "" {
		digest = digestOverride
	}
	obs := map[string]any{"evidence_id": "e1", "predicate": "session.ttl_seconds", "subject": "session", "value": 1200, "artifact_id": "tech_spec", "revision": "r1", "path": "spec.md", "source_sha256": digest, "locator": map[string]any{"kind": "span"}}
	if role != "" {
		obs["evidence_role"] = role
	}
	return map[string]any{"schema_version": pkgcollect.PackageSchema, "tech_spec": map[string]any{"artifact_id": "tech_spec", "content": content, "revision": "r1", "path": "spec.md"}, "observations": []any{obs}}
}

func TestCollectDerivesRoleFromPinnedArtifact(t *testing.T) {
	_, source, _, _ := runtime.Caller(0)
	root := filepath.Clean(filepath.Join(filepath.Dir(source), "..", "..", "..", "..", ".."))
	reg, err := predicates.Load(filepath.Join(root, "data", "adr_catalog"))
	if err != nil {
		t.Fatal(err)
	}
	got, err := pkgcollect.CollectObservations(fixture(t, "", ""), reg)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 1 || got[0]["evidence_role"] != "design_assertion" {
		t.Fatalf("observations=%#v", got)
	}
}

func TestCollectRejectsForgedRoleAndDigest(t *testing.T) {
	_, source, _, _ := runtime.Caller(0)
	root := filepath.Clean(filepath.Join(filepath.Dir(source), "..", "..", "..", "..", ".."))
	reg, err := predicates.Load(filepath.Join(root, "data", "adr_catalog"))
	if err != nil {
		t.Fatal(err)
	}
	for _, pkg := range []map[string]any{fixture(t, "implementation_fact", ""), fixture(t, "", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")} {
		if _, err := pkgcollect.CollectObservations(pkg, reg); err == nil {
			t.Fatalf("accepted forged provenance: %#v", pkg["observations"])
		}
	}
}

func TestCollectRejectsDuplicateArtifactIDs(t *testing.T) {
	_, source, _, _ := runtime.Caller(0)
	root := filepath.Clean(filepath.Join(filepath.Dir(source), "..", "..", "..", "..", ".."))
	reg, err := predicates.Load(filepath.Join(root, "data", "adr_catalog"))
	if err != nil {
		t.Fatal(err)
	}
	pkg := fixture(t, "", "")
	pkg["code"] = []any{map[string]any{"artifact_id": "tech_spec", "content": "package p", "path": "p.go", "revision": "r2"}}
	if _, err := pkgcollect.CollectObservations(pkg, reg); err == nil {
		t.Fatal("duplicate artifact identity accepted")
	}
}
