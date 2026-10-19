package pkgcollect_test

import (
	"path/filepath"
	"runtime"
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/collect/pkgcollect"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/evidence"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/predicates"
)

func catalogDir(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("no caller")
	}
	root := filepath.Clean(filepath.Join(filepath.Dir(file), "..", "..", "..", "..", ".."))
	return filepath.Join(root, "data", "adr_catalog")
}

func TestCollectUnknownPredicateFails(t *testing.T) {
	reg, err := predicates.Load(catalogDir(t))
	if err != nil {
		t.Fatal(err)
	}
	sha := "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
	pkg := map[string]any{
		"schema_version": pkgcollect.PackageSchema,
		"observations": []any{
			map[string]any{
				"evidence_id":   "e1",
				"predicate":     "not.a.real.predicate",
				"subject":       "svc",
				"value":         true,
				"artifact_id":   "tech_spec",
				"revision":      "sha256:" + sha,
				"path":          "spec.md",
				"source_sha256": sha,
				"locator":       map[string]any{"kind": "issue_claim", "value": "x"},
			},
		},
	}
	if _, err := pkgcollect.CollectObservations(pkg, reg); err == nil {
		t.Fatal("expected unknown predicate failure")
	}
}

func TestCollectAddsLocatorPrecision(t *testing.T) {
	reg, err := predicates.Load(catalogDir(t))
	if err != nil {
		t.Fatal(err)
	}
	content := "session ttl 3600 seconds\n"
	// digest of content computed by collect; omit sha256 to let it derive
	pkg := map[string]any{
		"schema_version": pkgcollect.PackageSchema,
		"tech_spec": map[string]any{
			"content": content,
			"path":    "spec.md",
		},
		"observations": []any{
			map[string]any{
				"evidence_id": "e-ttl",
				"predicate":   "session.ttl_seconds",
				"subject":     "auth",
				"value":       3600.0,
				"artifact_id": "tech_spec",
				"revision":    "rev1",
				"path":        "spec.md",
				"locator": map[string]any{
					"kind":           "paste_span",
					"line":           1,
					"start":          0,
					"end":            10,
					"excerpt_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
				},
			},
		},
	}
	out, err := pkgcollect.CollectObservations(pkg, reg)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 1 {
		t.Fatalf("len=%d", len(out))
	}
	if out[0]["locator_precision"] != evidence.PrecisionExact {
		t.Fatalf("precision=%v", out[0]["locator_precision"])
	}
	if out[0]["normalizer_version"] != evidence.NormalizerVersion {
		t.Fatalf("normalizer_version=%v", out[0]["normalizer_version"])
	}
	if out[0]["collector"] != pkgcollect.CollectorID {
		t.Fatalf("collector=%v", out[0]["collector"])
	}
}
