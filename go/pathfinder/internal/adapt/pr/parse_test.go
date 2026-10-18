package pr_test

import (
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/adapt/pr"
)

func TestParseRef(t *testing.T) {
	cases := []struct {
		in, repo string
		want     pr.Ref
		ok       bool
	}{
		{"https://github.com/tyler-beach/Platform/pull/54", "tyler-beach/Platform", pr.Ref{Owner: "tyler-beach", Repo: "Platform", Number: 54}, true},
		{"https://github.com/tyler-beach/Platform/pull/54/", "tyler-beach/Platform", pr.Ref{Owner: "tyler-beach", Repo: "Platform", Number: 54}, true},
		{"tyler-beach/Platform#54", "tyler-beach/Platform", pr.Ref{Owner: "tyler-beach", Repo: "Platform", Number: 54}, true},
		{"#54", "tyler-beach/Platform", pr.Ref{Owner: "tyler-beach", Repo: "Platform", Number: 54}, true},
		{"54", "tyler-beach/Platform", pr.Ref{Owner: "tyler-beach", Repo: "Platform", Number: 54}, true},
		{"https://github.com/other/other/pull/1", "tyler-beach/Platform", pr.Ref{}, false},
		{"https://evil.example/tyler-beach/Platform/pull/1", "tyler-beach/Platform", pr.Ref{}, false},
		{"", "tyler-beach/Platform", pr.Ref{}, false},
	}
	for _, tc := range cases {
		got, err := pr.ParseRef(tc.in, tc.repo)
		if tc.ok {
			if err != nil {
				t.Fatalf("%q: %v", tc.in, err)
			}
			if got != tc.want {
				t.Fatalf("%q: got %+v want %+v", tc.in, got, tc.want)
			}
			continue
		}
		if err == nil {
			t.Fatalf("%q: expected error", tc.in)
		}
	}
}

func TestDeniedPath(t *testing.T) {
	denied := []string{".env", ".env.local", "secrets/foo.pem", "id_rsa", "certs/server.key", "credentials.json"}
	for _, p := range denied {
		if !pr.IsDeniedPath(p) {
			t.Fatalf("expected deny %q", p)
		}
	}
	allowed := []string{"src/main.go", "docs/tech.md", "deploy/pdb.yaml"}
	for _, p := range allowed {
		if pr.IsDeniedPath(p) {
			t.Fatalf("expected allow %q", p)
		}
	}
}
