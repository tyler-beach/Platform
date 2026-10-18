package evaluate

import (
	"fmt"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/applicability"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/canonical"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/catalog"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/collect/pkgcollect"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/engine"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/extract/paste"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/modelobs"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/predicates"
)

const ReportSchema = "pathfinder-package-evaluation-v1"

// AggregateStatus maps per-requirement outcomes to a package-level status.
func AggregateStatus(outcomes []string) string {
	counts := map[string]int{}
	for _, o := range outcomes {
		counts[o]++
	}
	var applicable []string
	for _, o := range outcomes {
		if o != "not_applicable" {
			applicable = append(applicable, o)
		}
	}
	if len(outcomes) == 0 {
		return "insufficient_coverage"
	}
	if len(applicable) > 0 {
		allOK := true
		for _, o := range applicable {
			if o != "no_deviation_found" {
				allOK = false
				break
			}
		}
		if allOK {
			return "all_aligned"
		}
	}
	if len(applicable) == 0 && counts["not_applicable"] > 0 {
		return "not_applicable_only"
	}
	hasDev := counts["supported_deviation"] > 0
	hasOK := counts["no_deviation_found"] > 0
	hasInc := counts["inconclusive"] > 0
	if hasDev && !hasOK && !hasInc {
		return "deviations_found"
	}
	if hasDev || (hasOK && hasInc) || (hasDev && hasOK) {
		return "mixed"
	}
	if hasInc && !hasOK && !hasDev {
		return "insufficient_coverage"
	}
	if hasOK {
		return "all_aligned"
	}
	return "insufficient_coverage"
}

func aggregateMeaning(status string) string {
	switch status {
	case "all_aligned":
		return "All in-scope requirements with sufficient evidence are aligned."
	case "deviations_found":
		return "One or more in-scope requirements are supported deviations."
	case "mixed":
		return "Partial alignment: some requirements aligned, others deviant and/or inconclusive."
	case "insufficient_coverage":
		return "In-scope requirements lack sufficient evidence for confident results."
	case "not_applicable_only":
		return "No catalog requirements were in scope for this package."
	default:
		return ""
	}
}

// EvaluatePackage runs ensure-observations, collect, and engine evaluation.
func EvaluatePackage(packageObj map[string]any, catalogDir string, adrStatus string) (map[string]any, error) {
	return EvaluatePackageWithMode(packageObj, catalogDir, adrStatus, "")
}

// EvaluatePackageWithMode is EvaluatePackage plus optional catalog mode for identity metadata.
func EvaluatePackageWithMode(packageObj map[string]any, catalogDir string, adrStatus, catalogMode string) (map[string]any, error) {
	if adrStatus == "" {
		adrStatus = "accepted"
	}
	identity, err := catalog.LoadIdentity(catalogDir, catalogMode)
	if err != nil {
		return nil, err
	}
	reg, err := predicates.Load(catalogDir)
	if err != nil {
		return nil, err
	}
	rows, err := catalog.LoadRequirements(catalogDir, reg)
	if err != nil {
		return nil, err
	}
	subjects := catalog.SubjectMap(rows)
	ensured, err := paste.EnsureObservations(packageObj, subjects)
	if err != nil {
		return nil, err
	}
	if rawObs, ok := ensured["observations"].([]any); ok {
		aug, augErr := modelobs.Augment(rawObs)
		if augErr != nil {
			return nil, augErr
		}
		ensured["observations"] = aug
		if extraction, ok := ensured["extraction"].(map[string]any); ok {
			extraction["model_extract"] = modelobs.Enabled()
			extraction["observation_count"] = len(aug)
		}
	}
	observations, err := pkgcollect.CollectObservations(ensured, reg)
	if err != nil {
		return nil, err
	}
	obsAny := make([]any, len(observations))
	for i, o := range observations {
		obsAny[i] = o
	}

	pkgScope := applicability.ScopeFromPackage(ensured)
	var results []map[string]any
	var outcomes []string
	inScopeCount := 0
	for _, row := range rows {
		sm := applicability.InScope(pkgScope, applicability.MetaFromRow(row))
		if sm {
			inScopeCount++
		}
		decision, err := engine.Evaluate(catalog.RequirementForEngine(row), obsAny, adrStatus, sm)
		if err != nil {
			return nil, fmt.Errorf("evaluate %v: %w", row["requirement_id"], err)
		}
		label, _ := row["label_status"].(string)
		if label == "" {
			label = "synthetic_unadjudicated"
		}
		results = append(results, map[string]any{
			"adr_id":                row["adr_id"],
			"domain":                row["domain"],
			"title":                 row["title"],
			"requirement_id":        row["requirement_id"],
			"kind":                  row["kind"],
			"predicate":             row["predicate"],
			"subject":               row["subject"],
			"outcome":               decision["outcome"],
			"relationship":          decision["relationship"],
			"rationale":             decision["rationale"],
			"accepted_evidence_ids": decision["accepted_evidence_ids"],
			"uncertainty":           decision["uncertainty"],
			"result_sha256":         decision["result_sha256"],
			"label_status":          label,
			"in_scope":              sm,
		})
		outcomes = append(outcomes, decision["outcome"].(string))
	}
	counts := map[string]int{
		"supported_deviation": 0,
		"no_deviation_found":  0,
		"inconclusive":        0,
		"not_applicable":      0,
	}
	for _, o := range outcomes {
		counts[o]++
	}
	status := AggregateStatus(outcomes)
	pkgID, _ := ensured["package_id"].(string)
	if pkgID == "" {
		pkgID = "unnamed"
	}
	identity.Size = len(rows)
	catalogPath := catalogRelativePath(identity.Mode)
	report := map[string]any{
		"schema_version":     ReportSchema,
		"engine_version":     engine.EngineVersion,
		"package_id":         pkgID,
		"catalog_size":       len(rows),
		"in_scope_count":     inScopeCount,
		"catalog": map[string]any{
			"mode":              identity.Mode,
			"catalog_id":        identity.CatalogID,
			"version":           identity.Version,
			"manifest_sha256":   identity.ManifestSHA256,
			"path":              catalogPath,
			"requirement_count": identity.Size,
		},
		"observation_count": len(observations),
		"extraction":        ensured["extraction"],
		"aggregate_status":  status,
		"aggregate_meaning": aggregateMeaning(status),
		"counts":            counts,
		"results":           results,
	}
	fp, err := canonical.Fingerprint(report)
	if err != nil {
		return nil, err
	}
	report["report_sha256"] = fp
	return report, nil
}

func catalogRelativePath(mode string) string {
	if mode == catalog.ModeReal {
		return "data/adr_catalog"
	}
	return ".poc/requirement_catalog"
}
