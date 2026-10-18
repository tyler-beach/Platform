package issueintake_test

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/catalog"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/evaluate"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/issueintake"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/predicates"
)

func repoRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("caller")
	}
	return filepath.Clean(filepath.Join(filepath.Dir(file), "..", "..", "..", ".."))
}

func TestPackageFromPasteFixtureNoSourceEcho(t *testing.T) {
	root := repoRoot(t)
	catalogDir := filepath.Join(root, ".poc", "requirement_catalog")
	bodyPath := filepath.Join(root, ".poc", "issue_analyze", "fixtures", "paste_only_issue_body.md")
	body, err := os.ReadFile(bodyPath)
	if err != nil {
		t.Fatal(err)
	}
	reg, err := predicates.Load(catalogDir)
	if err != nil {
		t.Fatal(err)
	}
	rows, err := catalog.LoadRequirements(catalogDir, reg)
	if err != nil {
		t.Fatal(err)
	}
	pkg, err := issueintake.PackageFromIssue(string(body), 42, catalogDir, catalog.SubjectMap(rows), reg, issueintake.Options{})
	if err != nil {
		t.Fatal(err)
	}
	report, err := evaluate.EvaluatePackage(pkg, catalogDir, "accepted")
	if err != nil {
		t.Fatal(err)
	}
	comment, err := issueintake.RenderResultComment(report, pkg, "https://example.test/run")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(comment, issueintake.CommentMarker) {
		t.Fatal("missing comment marker")
	}
	if tech, ok := pkg["tech_spec"].(map[string]any); ok {
		if c, ok := tech["content"].(string); ok && len(c) > 40 && strings.Contains(comment, c) {
			t.Fatal("comment echoed tech_spec")
		}
	}
}
