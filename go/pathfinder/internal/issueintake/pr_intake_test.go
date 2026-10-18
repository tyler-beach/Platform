package issueintake_test

import (
	"fmt"
	"path/filepath"
	"strings"
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/adapt/pr"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/catalog"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/issueintake"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/predicates"
)

type fakePR struct {
	meta  pr.Meta
	files []pr.ChangedFile
	blobs map[string]string
}

func (f *fakePR) GetPR(owner, repo string, number int) (pr.Meta, error) { return f.meta, nil }
func (f *fakePR) ListChangedFiles(owner, repo string, number int) ([]pr.ChangedFile, error) {
	return f.files, nil
}
func (f *fakePR) GetFileContent(owner, repo, path, ref string) (string, error) {
	c, ok := f.blobs[path+"@"+ref]
	if !ok {
		return "", fmt.Errorf("missing")
	}
	return c, nil
}

func TestPackageFromIssuePROnlyOptionalTechSpec(t *testing.T) {
	root := repoRoot(t)
	catalogDir := filepath.Join(root, ".poc", "requirement_catalog")
	reg, err := predicates.Load(catalogDir)
	if err != nil {
		t.Fatal(err)
	}
	rows, err := catalog.LoadRequirements(catalogDir, reg)
	if err != nil {
		t.Fatal(err)
	}
	body := `### Public / synthetic attestation

- [X] I attest this submission contains only synthetic or explicitly public content and no secrets or confidential source.

### Same-repo pull request (optional)

#12

### Domains (optional scope filter)

identity, security
`
	client := &fakePR{
		meta: pr.Meta{
			Number: 12, HeadSHA: "deadbeef",
			HeadRepoFullName: "tyler-beach/Platform", BaseRepoFullName: "tyler-beach/Platform",
		},
		files: []pr.ChangedFile{{Path: "svc/session.go", Status: "modified"}},
		blobs: map[string]string{
			"svc/session.go@deadbeef": "package svc\nconst SessionTTLSeconds = 720\n",
		},
	}
	pkg, err := issueintake.PackageFromIssue(body, 7, catalogDir, catalog.SubjectMap(rows), reg, issueintake.Options{
		Repo:     "tyler-beach/Platform",
		PRClient: client,
	})
	if err != nil {
		t.Fatal(err)
	}
	code, _ := pkg["code"].([]any)
	if len(code) != 1 {
		t.Fatalf("expected PR code artifacts, got %d", len(code))
	}
	if _, hasTech := pkg["tech_spec"]; hasTech {
		t.Fatal("tech_spec should be optional/absent")
	}
	report := map[string]any{
		"aggregate_status":  "mixed",
		"aggregate_meaning": "test",
		"catalog_size":      100,
		"observation_count": 1,
		"report_sha256":     "abc",
		"counts": map[string]int{
			"supported_deviation": 1, "no_deviation_found": 0, "inconclusive": 0, "not_applicable": 0,
		},
		"results": []map[string]any{},
	}
	comment, err := issueintake.RenderResultComment(report, pkg, "https://example.invalid/run")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(comment, "github_pr_changed_files") || !strings.Contains(comment, "#12") {
		t.Fatalf("comment missing adapter summary: %s", comment)
	}
}
