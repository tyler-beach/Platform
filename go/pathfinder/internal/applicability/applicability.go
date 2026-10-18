package applicability

import (
	"strings"
)

// PackageScope is the pinned package's declared applicability context.
type PackageScope struct {
	Domains   []string
	Languages []string
}

// RequirementMeta is the catalog-side filter input for one requirement row.
type RequirementMeta struct {
	Domain               string
	LifecycleStatus      string
	ApplicabilityDomains []string
	ApplicabilityLangs   []string
}

// InScope reports whether a requirement should be evaluated for a package.
// Out-of-scope requirements MUST become not_applicable, never aligned.
func InScope(pkg PackageScope, req RequirementMeta) bool {
	if !lifecycleActive(req.LifecycleStatus) {
		return false
	}
	domains := req.ApplicabilityDomains
	if len(domains) == 0 && strings.TrimSpace(req.Domain) != "" {
		domains = []string{req.Domain}
	}
	if len(pkg.Domains) > 0 && !intersects(pkg.Domains, domains) {
		return false
	}
	if len(pkg.Languages) > 0 && len(req.ApplicabilityLangs) > 0 && !intersects(pkg.Languages, req.ApplicabilityLangs) {
		return false
	}
	return true
}

func lifecycleActive(status string) bool {
	switch strings.ToLower(strings.TrimSpace(status)) {
	case "", "proposed", "accepted", "active":
		return true
	default:
		return false
	}
}

func intersects(a, b []string) bool {
	if len(b) == 0 {
		// Requirement did not constrain this dimension.
		return true
	}
	set := map[string]struct{}{}
	for _, x := range a {
		set[strings.ToLower(strings.TrimSpace(x))] = struct{}{}
	}
	for _, y := range b {
		if _, ok := set[strings.ToLower(strings.TrimSpace(y))]; ok {
			return true
		}
	}
	return false
}

// ScopeFromPackage extracts PackageScope from a pinned package object.
func ScopeFromPackage(packageObj map[string]any) PackageScope {
	out := PackageScope{}
	scope, _ := packageObj["scope"].(map[string]any)
	if scope == nil {
		return out
	}
	out.Domains = stringSlice(scope["domains"])
	out.Languages = stringSlice(scope["languages"])
	return out
}

// MetaFromRow projects catalog row fields into RequirementMeta.
func MetaFromRow(row map[string]any) RequirementMeta {
	meta := RequirementMeta{
		Domain:          stringField(row["domain"]),
		LifecycleStatus: stringField(row["lifecycle_status"]),
	}
	if app, ok := row["applicability"].(map[string]any); ok {
		meta.ApplicabilityDomains = stringSlice(app["domains"])
		meta.ApplicabilityLangs = stringSlice(app["languages"])
	}
	return meta
}

func stringField(v any) string {
	s, _ := v.(string)
	return s
}

func stringSlice(v any) []string {
	switch t := v.(type) {
	case []string:
		return append([]string{}, t...)
	case []any:
		var out []string
		for _, item := range t {
			if s, ok := item.(string); ok && strings.TrimSpace(s) != "" {
				out = append(out, s)
			}
		}
		return out
	default:
		return nil
	}
}
