package pr_test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/adapt/pr"
)

type fakeClient struct {
	meta  pr.Meta
	files []pr.ChangedFile
	blobs map[string]string
	err   error
}

func (f *fakeClient) GetPR(owner, repo string, number int) (pr.Meta, error) {
	if f.err != nil {
		return pr.Meta{}, f.err
	}
	return f.meta, nil
}
func (f *fakeClient) ListChangedFiles(owner, repo string, number int) ([]pr.ChangedFile, error) {
	return f.files, nil
}
func (f *fakeClient) GetFileContent(owner, repo, path, ref string) (string, error) {
	key := path + "@" + ref
	c, ok := f.blobs[key]
	if !ok {
		return "", fmt.Errorf("missing %s", key)
	}
	return c, nil
}

func TestResolveSameRepoChangedFiles(t *testing.T) {
	client := &fakeClient{
		meta: pr.Meta{
			Number: 7, HeadSHA: "abc123",
			HeadRepoFullName: "acme/app", BaseRepoFullName: "acme/app", IsFork: false,
		},
		files: []pr.ChangedFile{
			{Path: "src/session.go", Status: "modified"},
			{Path: ".env", Status: "added"},
			{Path: "gone.txt", Status: "removed"},
		},
		blobs: map[string]string{
			"src/session.go@abc123": "package main\nconst SessionTTL = 720\n",
		},
	}
	res, err := pr.Resolve(client, "acme/app", "#7", 99)
	if err != nil {
		t.Fatal(err)
	}
	code, _ := res.Package["code"].([]any)
	if len(code) != 1 {
		t.Fatalf("code=%d limitations=%v", len(code), res.Limitations)
	}
	block := code[0].(map[string]any)
	if block["path"] != "src/session.go" || block["revision"] != "git:abc123" {
		t.Fatalf("block=%v", block)
	}
	joined := strings.Join(res.Limitations, "\n")
	if !strings.Contains(joined, "denylisted") {
		t.Fatalf("expected denylist limitation, got %v", res.Limitations)
	}
}

func TestResolveForkDenied(t *testing.T) {
	client := &fakeClient{
		meta: pr.Meta{
			Number: 1, HeadSHA: "x",
			HeadRepoFullName: "attacker/app", BaseRepoFullName: "acme/app", IsFork: true,
		},
	}
	_, err := pr.Resolve(client, "acme/app", "https://github.com/acme/app/pull/1", 1)
	if err == nil || !strings.Contains(err.Error(), "fork") {
		t.Fatalf("expected fork denial, got %v", err)
	}
}

func TestResolveTotalCapFailsClosed(t *testing.T) {
	big := strings.Repeat("a", 600_000)
	client := &fakeClient{
		meta: pr.Meta{Number: 2, HeadSHA: "h", HeadRepoFullName: "acme/app", BaseRepoFullName: "acme/app"},
		files: []pr.ChangedFile{
			{Path: "a.txt", Status: "added"},
			{Path: "b.txt", Status: "added"},
		},
		blobs: map[string]string{
			"a.txt@h": big,
			"b.txt@h": big,
		},
	}
	// Each file over MaxFileBytes is skipped; ensure no package if nothing left.
	_, err := pr.Resolve(client, "acme/app", "#2", 1)
	if err == nil {
		t.Fatal("expected failure when no fetchable files within caps")
	}
}
