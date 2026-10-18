package applicability_test

import (
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/applicability"
)

func TestOutOfScopeDomainIsNotInScope(t *testing.T) {
	ok := applicability.InScope(
		applicability.PackageScope{Domains: []string{"identity"}},
		applicability.RequirementMeta{Domain: "cloud"},
	)
	if ok {
		t.Fatal("cloud requirement must be out of scope for identity package")
	}
}

func TestMatchingDomainIsInScope(t *testing.T) {
	ok := applicability.InScope(
		applicability.PackageScope{Domains: []string{"identity"}},
		applicability.RequirementMeta{Domain: "identity", LifecycleStatus: "proposed"},
	)
	if !ok {
		t.Fatal("expected in scope")
	}
}

func TestEmptyPackageDomainsKeepsActiveRequirements(t *testing.T) {
	ok := applicability.InScope(
		applicability.PackageScope{},
		applicability.RequirementMeta{Domain: "reliability", LifecycleStatus: "accepted"},
	)
	if !ok {
		t.Fatal("empty package domains should not filter active requirements")
	}
}

func TestDeprecatedLifecycleIsOutOfScope(t *testing.T) {
	ok := applicability.InScope(
		applicability.PackageScope{},
		applicability.RequirementMeta{Domain: "identity", LifecycleStatus: "deprecated"},
	)
	if ok {
		t.Fatal("deprecated requirements must be out of scope")
	}
}

func TestLanguageMismatchIsOutOfScope(t *testing.T) {
	ok := applicability.InScope(
		applicability.PackageScope{Languages: []string{"go"}},
		applicability.RequirementMeta{
			Domain:             "identity",
			LifecycleStatus:    "accepted",
			ApplicabilityLangs: []string{"python"},
		},
	)
	if ok {
		t.Fatal("language mismatch must be out of scope")
	}
}

func TestScopeFromPackageAndMetaFromRow(t *testing.T) {
	pkg := map[string]any{
		"scope": map[string]any{
			"domains":   []any{"identity", "security"},
			"languages": []any{"go"},
		},
	}
	scope := applicability.ScopeFromPackage(pkg)
	if len(scope.Domains) != 2 || scope.Languages[0] != "go" {
		t.Fatalf("scope=%+v", scope)
	}
	row := map[string]any{
		"domain":            "identity",
		"lifecycle_status":  "proposed",
		"applicability":     map[string]any{"domains": []any{"identity"}, "languages": []any{"go"}},
	}
	meta := applicability.MetaFromRow(row)
	if !applicability.InScope(scope, meta) {
		t.Fatal("expected row meta in scope")
	}
}
