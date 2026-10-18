package pr

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os/exec"
	"strconv"
	"strings"
)

// GHClient uses the gh CLI against the GitHub API.
type GHClient struct {
	Run func(args ...string) ([]byte, error)
}

// NewGHClient returns a client that shells out to gh.
func NewGHClient() *GHClient {
	return &GHClient{
		Run: func(args ...string) ([]byte, error) {
			cmd := exec.Command("gh", args...)
			out, err := cmd.Output()
			if err != nil {
				if ee, ok := err.(*exec.ExitError); ok {
					return nil, fmt.Errorf("gh %s: %s", strings.Join(args, " "), strings.TrimSpace(string(ee.Stderr)))
				}
				return nil, err
			}
			return out, nil
		},
	}
}

func (c *GHClient) GetPR(owner, repo string, number int) (Meta, error) {
	raw, err := c.Run("api", fmt.Sprintf("repos/%s/%s/pulls/%d", owner, repo, number))
	if err != nil {
		return Meta{}, err
	}
	var payload struct {
		Number int `json:"number"`
		Head   struct {
			SHA  string `json:"sha"`
			Repo *struct {
				FullName string `json:"full_name"`
			} `json:"repo"`
		} `json:"head"`
		Base struct {
			Repo struct {
				FullName string `json:"full_name"`
			} `json:"repo"`
		} `json:"base"`
		HeadRepo *struct {
			FullName string `json:"full_name"`
		} `json:"head_repository"`
	}
	if err := json.Unmarshal(raw, &payload); err != nil {
		return Meta{}, err
	}
	headName := ""
	if payload.Head.Repo != nil {
		headName = payload.Head.Repo.FullName
	}
	isFork := headName != "" && !strings.EqualFold(headName, payload.Base.Repo.FullName)
	return Meta{
		Number:           payload.Number,
		HeadSHA:          payload.Head.SHA,
		HeadRepoFullName: headName,
		BaseRepoFullName: payload.Base.Repo.FullName,
		IsFork:           isFork,
	}, nil
}

func (c *GHClient) ListChangedFiles(owner, repo string, number int) ([]ChangedFile, error) {
	raw, err := c.Run("api", "--paginate", fmt.Sprintf("repos/%s/%s/pulls/%d/files", owner, repo, number))
	if err != nil {
		return nil, err
	}
	var files []struct {
		Filename string `json:"filename"`
		Status   string `json:"status"`
	}
	if err := json.Unmarshal(raw, &files); err != nil {
		return nil, err
	}
	out := make([]ChangedFile, 0, len(files))
	for _, f := range files {
		out = append(out, ChangedFile{Path: f.Filename, Status: f.Status})
	}
	return out, nil
}

func (c *GHClient) GetFileContent(owner, repo, path, ref string) (string, error) {
	raw, err := c.Run("api", fmt.Sprintf("repos/%s/%s/contents/%s?ref=%s", owner, repo, path, ref))
	if err != nil {
		return "", err
	}
	var payload struct {
		Encoding string `json:"encoding"`
		Content  string `json:"content"`
		Type     string `json:"type"`
		Size     int    `json:"size"`
	}
	if err := json.Unmarshal(raw, &payload); err != nil {
		return "", err
	}
	if payload.Type != "" && payload.Type != "file" {
		return "", fmt.Errorf("not a file")
	}
	if payload.Encoding != "base64" {
		return "", fmt.Errorf("unsupported content encoding %q", payload.Encoding)
	}
	// GitHub may wrap base64 with newlines.
	cleaned := strings.Map(func(r rune) rune {
		if r == '\n' || r == '\r' || r == ' ' {
			return -1
		}
		return r
	}, payload.Content)
	decoded, err := base64.StdEncoding.DecodeString(cleaned)
	if err != nil {
		return "", err
	}
	_ = strconv.Itoa(payload.Size)
	return string(decoded), nil
}
