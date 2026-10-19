package evaluate

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"strings"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/applicability"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/canonical"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/catalog"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/collect/pkgcollect"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/engine"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/extract/paste"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/modelobs"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/predicates"
)

const ReportSchema = "pathfinder-package-evaluation-v2"

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
	ensured := clonePackage(packageObj)
	callerObservations := hasObservations(ensured["observations"])
	var observations []map[string]any
	var extraction map[string]any
	if callerObservations {
		observations, err = pkgcollect.CollectObservations(ensured, reg)
		extraction = map[string]any{"extractor": "provided_observations", "status": "provided"}
	} else {
		// Semantic extraction is opt-in. When unavailable, retain the deterministic
		// extractor and label its actual coverage instead of implying semantic work.
		if modelobs.Enabled() {
			semantic := runSemanticExtraction(ensured, rows, reg)
			if semantic != nil && semantic["err"] == nil {
				result := semantic["result"].(modelobs.Result)
				extraction = result.Metadata
				if len(result.Observations) > 0 {
					semanticAny := make([]any, len(result.Observations))
					for i, o := range result.Observations {
						semanticAny[i] = o
					}
					ensured["observations"] = semanticAny
					observations, err = pkgcollect.CollectObservations(ensured, reg)
				}
			} else if semantic != nil {
				extraction = semantic["metadata"].(map[string]any)
			}
		}
		if len(observations) == 0 {
			fallback, fallbackErr := paste.EnsureObservations(ensured, subjects)
			if fallbackErr != nil {
				return nil, fallbackErr
			}
			ensured = fallback
			observations, err = pkgcollect.CollectObservations(ensured, reg)
			if extraction == nil {
				extraction, _ = ensured["extraction"].(map[string]any)
				if extraction == nil {
					extraction = map[string]any{}
				}
				extraction["status"] = "deterministic_fallback"
			} else {
				extraction["fallback_extractor"] = paste.ExtractorID
				extraction["fallback_observation_count"] = len(observations)
			}
		}
	}
	if err != nil {
		return nil, err
	}
	if extraction == nil {
		extraction = map[string]any{"extractor": "none", "status": "no_evidence"}
	}
	extraction["observation_count"] = len(observations)
	ensured["extraction"] = extraction
	pkgScope := applicability.ScopeFromPackage(ensured)
	var results []map[string]any
	var outcomes []string
	evidenceRoleCounts := map[string]int{}
	observationValues := make([]any, 0, len(observations))
	for _, observation := range observations {
		observationValues = append(observationValues, observation)
		if role, ok := observation["evidence_role"].(string); ok && role != "" {
			evidenceRoleCounts[role]++
		}
	}
	inScopeCount := 0
	for _, row := range rows {
		sm := applicability.InScope(pkgScope, applicability.MetaFromRow(row))
		if sm {
			inScopeCount++
		}
		decision, err := engine.Evaluate(catalog.RequirementForEngine(row), observationValues, adrStatus, sm)
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
			"provenance":            decision["provenance"],
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
		"schema_version": ReportSchema,
		"engine_version": engine.EngineVersion,
		"package_id":     pkgID,
		"catalog_size":   len(rows),
		"in_scope_count": inScopeCount,
		"catalog": map[string]any{
			"mode":              identity.Mode,
			"catalog_id":        identity.CatalogID,
			"version":           identity.Version,
			"manifest_sha256":   identity.ManifestSHA256,
			"path":              catalogPath,
			"requirement_count": identity.Size,
		},
		"observation_count":    len(observations),
		"result_count":         len(results),
		"extraction":           extraction,
		"evidence_role_counts": evidenceRoleCounts,
		"aggregate_status":     status,
		"aggregate_meaning":    aggregateMeaning(status),
		"counts":               counts,
		"results":              results,
	}
	fp, err := canonical.Fingerprint(report)
	if err != nil {
		return nil, err
	}
	report["report_sha256"] = fp
	return report, nil
}

func clonePackage(pkg map[string]any) map[string]any {
	out := make(map[string]any, len(pkg))
	for k, v := range pkg {
		out[k] = v
	}
	return out
}
func hasObservations(value any) bool {
	switch xs := value.(type) {
	case []any:
		return len(xs) > 0
	case []map[string]any:
		return len(xs) > 0
	}
	return false
}
func runSemanticExtraction(pkg map[string]any, rows []map[string]any, reg *predicates.Registry) map[string]any {
	artifacts := []modelobs.SourceArtifact{}
	if block, ok := pkg["tech_spec"].(map[string]any); ok {
		if content, ok := block["content"].(string); ok && content != "" {
			artifacts = append(artifacts, modelobs.SourceArtifact{ID: stringField(block, "artifact_id", "tech_spec"), Kind: "technical_specification", Role: modelobs.RoleDesignAssertion, Path: stringField(block, "path", "issue/tech-spec.md"), Revision: stringField(block, "revision", "sha256:"+sha(content)), Content: content})
		}
	}
	code, _ := pkg["code"].([]any)
	for i, raw := range code {
		b, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		content, _ := b["content"].(string)
		if content == "" {
			continue
		}
		id := stringField(b, "artifact_id", fmt.Sprintf("code-%d", i))
		artifacts = append(artifacts, modelobs.SourceArtifact{ID: id, Kind: "implementation", Role: modelobs.RoleImplementationFact, Path: stringField(b, "path", id), Revision: stringField(b, "revision", "sha256:"+sha(content)), Content: content})
	}
	byPredicate := map[string]map[string]bool{}
	pkgScope := applicability.ScopeFromPackage(pkg)
	for _, row := range rows {
		if !applicability.InScope(pkgScope, applicability.MetaFromRow(row)) {
			continue
		}
		p, _ := row["predicate"].(string)
		s, _ := row["subject"].(string)
		if p != "" && s != "" {
			if byPredicate[p] == nil {
				byPredicate[p] = map[string]bool{}
			}
			byPredicate[p][s] = true
		}
	}
	allowed := []modelobs.AllowedPredicate{}
	for p, ss := range byPredicate {
		meta, e := reg.Get(p)
		if e != nil || meta.ValueType == "" {
			continue
		}
		cs, e := reg.CollectorsFor(p)
		if e != nil {
			continue
		}
		can := false
		for _, c := range cs {
			if c == "structured_package" {
				can = true
			}
		}
		if !can {
			continue
		}
		subjects := []string{}
		for s := range ss {
			subjects = append(subjects, s)
		}
		allowed = append(allowed, modelobs.AllowedPredicate{Predicate: p, ValueType: meta.ValueType, Subjects: subjects, Description: meta.Description})
	}
	model := strings.TrimSpace(os.Getenv("ANTHROPIC_MODEL"))
	key := os.Getenv("ANTHROPIC_API_KEY")
	result, err := modelobs.NewClient(modelobs.Config{APIKey: key, Model: model}, nil).Normalize(context.Background(), artifacts, allowed)
	if err != nil {
		return map[string]any{"err": err, "metadata": result.Metadata}
	}
	return map[string]any{"result": result}
}
func stringField(m map[string]any, key, fallback string) string {
	if s, ok := m[key].(string); ok && s != "" {
		return s
	}
	return fallback
}
func sha(content string) string {
	sum := sha256.Sum256([]byte(content))
	return hex.EncodeToString(sum[:])
}

func catalogRelativePath(mode string) string {
	if mode == catalog.ModeReal {
		return "data/adr_catalog"
	}
	return ".poc/requirement_catalog"
}
