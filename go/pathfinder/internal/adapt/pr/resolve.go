package pr

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strings"
	"unicode/utf8"
)

const (
	MaxFiles     = 50
	MaxTotalBytes = 1 << 20 // 1 MiB
	MaxFileBytes = 50_000
)

// Meta describes a pull request head for pinning.
type Meta struct {
	Number           int
	HeadSHA          string
	HeadRepoFullName string
	BaseRepoFullName string
	IsFork           bool
}

// ChangedFile is a PR file entry (metadata only).
type ChangedFile struct {
	Path   string
	Status string
}

// Client fetches PR metadata and file contents from GitHub.
type Client interface {
	GetPR(owner, repo string, number int) (Meta, error)
	ListChangedFiles(owner, repo string, number int) ([]ChangedFile, error)
	GetFileContent(owner, repo, path, ref string) (string, error)
}

// Result is a pinned package fragment plus limitations.
type Result struct {
	Package     map[string]any
	Limitations []string
}

// Resolve builds a pathfinder-evidence-package-v1 from a same-repo PR's changed files.
func Resolve(client Client, trustedRepo string, refText string, issueNumber int) (Result, error) {
	ref, err := ParseRef(refText, trustedRepo)
	if err != nil {
		return Result{}, err
	}
	meta, err := client.GetPR(ref.Owner, ref.Repo, ref.Number)
	if err != nil {
		return Result{}, fmt.Errorf("fetch pull request: %w", err)
	}
	if meta.IsFork || !strings.EqualFold(meta.HeadRepoFullName, trustedRepo) {
		return Result{}, fmt.Errorf("fork pull requests are denied (head %q, trusted %q)", meta.HeadRepoFullName, trustedRepo)
	}
	if meta.HeadSHA == "" {
		return Result{}, fmt.Errorf("pull request head SHA missing")
	}

	files, err := client.ListChangedFiles(ref.Owner, ref.Repo, ref.Number)
	if err != nil {
		return Result{}, fmt.Errorf("list changed files: %w", err)
	}

	var limitations []string
	var code []any
	total := 0
	fetched := 0
	for _, f := range files {
		status := strings.ToLower(f.Status)
		if status == "removed" || status == "deleted" {
			continue
		}
		if strings.Contains(f.Path, "..") || strings.HasPrefix(f.Path, "/") {
			limitations = append(limitations, "skipped unsafe path: "+f.Path)
			continue
		}
		if IsDeniedPath(f.Path) {
			limitations = append(limitations, "skipped denylisted path: "+f.Path)
			continue
		}
		if fetched >= MaxFiles {
			limitations = append(limitations, fmt.Sprintf("file count cap %d reached; remaining files skipped", MaxFiles))
			break
		}
		content, err := client.GetFileContent(ref.Owner, ref.Repo, f.Path, meta.HeadSHA)
		if err != nil {
			limitations = append(limitations, fmt.Sprintf("skipped %s: %v", f.Path, err))
			continue
		}
		if !utf8.ValidString(content) || looksBinary(content) {
			limitations = append(limitations, "skipped binary/non-utf8 path: "+f.Path)
			continue
		}
		if len(content) > MaxFileBytes {
			limitations = append(limitations, fmt.Sprintf("skipped oversize file %s (%d bytes)", f.Path, len(content)))
			continue
		}
		if total+len(content) > MaxTotalBytes {
			return Result{}, fmt.Errorf("PR changed-file pack exceeds %d bytes total", MaxTotalBytes)
		}
		digest := sha256Hex(content)
		code = append(code, map[string]any{
			"artifact_id": fmt.Sprintf("pr-%d-%d", ref.Number, fetched),
			"path":        f.Path,
			"revision":    "git:" + meta.HeadSHA,
			"sha256":      digest,
			"content":     content,
		})
		total += len(content)
		fetched++
	}
	if len(code) == 0 {
		return Result{}, fmt.Errorf("no fetchable text files from pull request #%d after filters", ref.Number)
	}

	pkg := map[string]any{
		"schema_version": "pathfinder-evidence-package-v1",
		"package_id":     fmt.Sprintf("github-issue-%d-pr-%d", issueNumber, ref.Number),
		"scope":          map[string]any{},
		"code":           code,
		"observations":   []any{},
		"adapter": map[string]any{
			"kind":        "github_pr_changed_files",
			"pr_number":   ref.Number,
			"head_sha":    meta.HeadSHA,
			"repository":  trustedRepo,
			"file_count":  len(code),
			"limitations": limitations,
		},
	}
	return Result{Package: pkg, Limitations: limitations}, nil
}

func sha256Hex(content string) string {
	sum := sha256.Sum256([]byte(content))
	return hex.EncodeToString(sum[:])
}

func looksBinary(content string) bool {
	// NUL byte is a strong binary signal.
	return strings.ContainsRune(content, 0)
}
