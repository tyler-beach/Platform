package pr

import (
	"fmt"
	"net/url"
	"path"
	"regexp"
	"strconv"
	"strings"
)

// Ref identifies a pull request in a GitHub repository.
type Ref struct {
	Owner  string
	Repo   string
	Number int
}

var (
	hashRefRE   = regexp.MustCompile(`^([^/\s]+)/([^/\s]+)#(\d+)$`)
	bareNumRE   = regexp.MustCompile(`^#?(\d+)$`)
	denyPathRes = []*regexp.Regexp{
		regexp.MustCompile(`(?i)(^|/)\.env(\.|$)`),
		regexp.MustCompile(`(?i)\.pem$`),
		regexp.MustCompile(`(?i)\.key$`),
		regexp.MustCompile(`(?i)(^|/)id_rsa`),
		regexp.MustCompile(`(?i)(^|/)credentials[^/]*$`),
		regexp.MustCompile(`(?i)\.p12$`),
		regexp.MustCompile(`(?i)\.pfx$`),
	}
)

// ParseRef parses a PR URL, owner/repo#n, #n, or n against the trusted repository.
// Cross-repo and non-github.com hosts fail closed.
func ParseRef(raw, trustedRepo string) (Ref, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return Ref{}, fmt.Errorf("empty pull request reference")
	}
	owner, repo, err := splitRepo(trustedRepo)
	if err != nil {
		return Ref{}, err
	}

	if m := hashRefRE.FindStringSubmatch(raw); m != nil {
		n, _ := strconv.Atoi(m[3])
		ref := Ref{Owner: m[1], Repo: m[2], Number: n}
		if !sameRepo(ref, owner, repo) {
			return Ref{}, fmt.Errorf("cross-repo pull request denied: %s/%s (trusted %s)", ref.Owner, ref.Repo, trustedRepo)
		}
		return ref, nil
	}
	if m := bareNumRE.FindStringSubmatch(raw); m != nil {
		n, _ := strconv.Atoi(m[1])
		return Ref{Owner: owner, Repo: repo, Number: n}, nil
	}

	u, err := url.Parse(raw)
	if err != nil || u.Scheme == "" || u.Host == "" {
		return Ref{}, fmt.Errorf("unrecognized pull request reference %q", raw)
	}
	host := strings.ToLower(u.Hostname())
	if host != "github.com" && host != "www.github.com" {
		return Ref{}, fmt.Errorf("pull request host %q is not github.com", host)
	}
	parts := strings.Split(strings.Trim(u.Path, "/"), "/")
	// owner/repo/pull/n
	if len(parts) < 4 || parts[2] != "pull" {
		return Ref{}, fmt.Errorf("unrecognized github pull request URL path %q", u.Path)
	}
	n, err := strconv.Atoi(parts[3])
	if err != nil || n <= 0 {
		return Ref{}, fmt.Errorf("invalid pull request number in %q", raw)
	}
	ref := Ref{Owner: parts[0], Repo: parts[1], Number: n}
	if !sameRepo(ref, owner, repo) {
		return Ref{}, fmt.Errorf("cross-repo pull request denied: %s/%s (trusted %s)", ref.Owner, ref.Repo, trustedRepo)
	}
	return ref, nil
}

// IsDeniedPath reports whether a changed path should be skipped (secret-ish).
func IsDeniedPath(p string) bool {
	p = path.Clean("/" + strings.ReplaceAll(p, "\\", "/"))
	p = strings.TrimPrefix(p, "/")
	if strings.Contains(p, "..") {
		return true
	}
	base := path.Base(p)
	for _, re := range denyPathRes {
		if re.MatchString(p) || re.MatchString(base) {
			return true
		}
	}
	return false
}

func splitRepo(trusted string) (owner, repo string, err error) {
	parts := strings.Split(trusted, "/")
	if len(parts) != 2 || parts[0] == "" || parts[1] == "" {
		return "", "", fmt.Errorf("invalid trusted repository %q", trusted)
	}
	return parts[0], parts[1], nil
}

func sameRepo(ref Ref, owner, repo string) bool {
	return strings.EqualFold(ref.Owner, owner) && strings.EqualFold(ref.Repo, repo)
}
