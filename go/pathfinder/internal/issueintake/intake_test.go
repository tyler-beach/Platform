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

func TestCatalogModeFromIssueBody(t *testing.T) {
	if got := issueintake.CatalogModeFromIssueBody("### Catalog pack\n\nSynthetic demo catalog (ADR-101–200)\n"); got != "synthetic" {
		t.Fatalf("got %q", got)
	}
	if got := issueintake.CatalogModeFromIssueBody("### Catalog pack\n\nReal prototype pack (default)\n"); got != "real" {
		t.Fatalf("got %q", got)
	}
	if got := issueintake.CatalogModeFromIssueBody("### Domains\n\nidentity\n"); got != "" {
		t.Fatalf("empty want, got %q", got)
	}
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
	_ = comment
	if tech, ok := pkg["tech_spec"].(map[string]any); ok {
		if c, ok := tech["content"].(string); ok && len(c) > 40 && strings.Contains(comment, c) {
			t.Fatal("comment echoed tech_spec")
		}
	}
}

func TestResultCommentShowsUnifiedConflictingEvidenceAndSources(t *testing.T) {
	comment, err := issueintake.RenderResultComment(map[string]any{
		"aggregate_status": "insufficient_coverage",
		"counts":           map[string]int{"inconclusive": 1},
		"results": []map[string]any{{
			"adr_id":       "ADR-1",
			"domain":       "identity",
			"outcome":      "inconclusive",
			"relationship": "conflicting_evidence",
			"predicate":    "session.ttl_seconds",
			"provenance": []map[string]any{
				{"evidence_role": "design_assertion", "path": "spec.md"},
				{"evidence_role": "implementation_fact", "path": "session.go"},
			},
		}},
	}, map[string]any{}, "https://example.test/run")
	if err != nil {
		t.Fatal(err)
	}
	for _, want := range []string{"conflicting evidence", "design_assertion: <code>spec.md</code>", "implementation_fact: <code>session.go</code>"} {
		if !strings.Contains(comment, want) {
			t.Fatalf("comment missing %q:\n%s", want, comment)
		}
	}
}
