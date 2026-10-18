package catalog_test

import (
	"path/filepath"
	"runtime"
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/catalog"
)

func repoRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("no caller")
	}
	return filepath.Clean(filepath.Join(filepath.Dir(file), "..", "..", "..", ".."))
}

func TestResolveDirModes(t *testing.T) {
	root := repoRoot(t)
	syn, err := catalog.ResolveDir(root, "synthetic")
	if err != nil {
		t.Fatal(err)
	}
	if syn != catalog.DefaultDir(root) {
		t.Fatalf("synthetic=%s", syn)
	}
	real, err := catalog.ResolveDir(root, "real")
	if err != nil {
		t.Fatal(err)
	}
	if real != filepath.Join(root, "data", "adr_catalog") {
		t.Fatalf("real=%s", real)
	}
	id, err := catalog.LoadIdentity(real, "real")
	if err != nil {
		t.Fatal(err)
	}
	if id.CatalogID != "platform-real-adr-v0" || id.ManifestSHA256 == "" {
		t.Fatalf("identity=%+v", id)
	}
}
