package issueintake

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"html"
	"regexp"
	"strings"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/adapt/pr"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/collect/pkgcollect"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/predicates"
)

// Options configures optional GitHub adapters for intake.
type Options struct {
	Repo     string    // trusted owner/repo (GITHUB_REPOSITORY)
	PRClient pr.Client // nil disables PR adapter
}

const (
	MaxFieldChars   = 50_000
	MaxPackageChars = 200_000
	CommentMarker   = "<!-- pathfinder-analyze-report -->"
)

var (
	packageFenceRE = regexp.MustCompile(`(?is)` + "```(?:pathfinder-package|json)\\s*\\n(.*?)\\n```")
	sectionHeadRE  = regexp.MustCompile(`(?m)^###\s+(.+?)\s*$`)
)

type Error struct{ Msg string }

func (e *Error) Error() string { return e.Msg }

func sha(content string) string {
	sum := sha256.Sum256([]byte(content))
	return hex.EncodeToString(sum[:])
}

func normalizeTitle(title string) string {
	return strings.Join(strings.Fields(strings.ToLower(strings.TrimSpace(title))), " ")
}

// ParseFormSections extracts ### sections from an issue body.
func ParseFormSections(body string) map[string]string {
	sections := map[string]string{}
	indexes := sectionHeadRE.FindAllStringSubmatchIndex(body, -1)
	for i, loc := range indexes {
		title := body[loc[2]:loc[3]]
		start := loc[1]
		end := len(body)
		if i+1 < len(indexes) {
			end = indexes[i+1][0]
		}
		sections[normalizeTitle(title)] = strings.TrimSpace(body[start:end])
	}
	return sections
}

func AttestationAccepted(body string, sections map[string]string) bool {
	var b strings.Builder
	b.WriteString(body)
	b.WriteByte('\n')
	for _, v := range sections {
		b.WriteString(v)
		b.WriteByte('\n')
	}
	text := b.String()
	patterns := []*regexp.Regexp{
		regexp.MustCompile(`(?i)\[x\].*synthetic or explicitly public`),
		regexp.MustCompile(`(?i)\[X\].*synthetic or explicitly public`),
		regexp.MustCompile(`(?is)attestation.*\n.*\[x\]`),
	}
	for _, p := range patterns {
		if p.MatchString(text) {
			return true
		}
	}
	return false
}

func extractPackageJSON(body string, sections map[string]string) (map[string]any, error) {
	for _, key := range []string{"full package json (preferred)", "full package json", "package json"} {
		if raw, ok := sections[key]; ok && strings.TrimSpace(raw) != "" {
			return parsePackageRaw(raw)
		}
	}
	if m := packageFenceRE.FindStringSubmatch(body); m != nil {
		return parsePackageRaw(m[1])
	}
	return nil, nil
}

func parsePackageRaw(raw string) (map[string]any, error) {
	raw = strings.TrimSpace(raw)
	if m := packageFenceRE.FindStringSubmatch(raw); m != nil {
		raw = strings.TrimSpace(m[1])
	}
	if len(raw) > MaxPackageChars {
		return nil, &Error{Msg: fmt.Sprintf("package JSON exceeds %d characters", MaxPackageChars)}
	}
	var value map[string]any
	if err := json.Unmarshal([]byte(raw), &value); err != nil {
		return nil, &Error{Msg: fmt.Sprintf("full package JSON is invalid: %v", err)}
	}
	return value, nil
}

func bounded(label, value string) (string, error) {
	if len(value) > MaxFieldChars {
		return "", &Error{Msg: fmt.Sprintf("%s exceeds %d characters", label, MaxFieldChars)}
	}
	return value, nil
}

func guessCodePath(code string) string {
	if strings.Contains(code, "package main") || regexp.MustCompile(`\bfunc\s+\w+\s*\(`).MatchString(code) {
		return "issue/sample.go"
	}
	if regexp.MustCompile(`(?m)^\s*(def|class|import|from)\s+`).MatchString(code) || strings.Contains(code, "async def") {
		return "issue/sample.py"
	}
	if regexp.MustCompile(`(?m)^(apiVersion|kind):\s*\S+`).MatchString(code) {
		return "issue/manifest.yaml"
	}
	if strings.HasPrefix(strings.TrimLeft(code, " \t"), "{") {
		return "issue/config.json"
	}
	return "issue/sample-code.txt"
}

func buildPackageFromFields(sections map[string]string, issueNumber int, allowEmpty bool) (map[string]any, error) {
	tech, err := bounded("tech spec", firstSection(sections, "tech spec (markdown)", "tech spec"))
	if err != nil {
		return nil, err
	}
	code, err := bounded("sample code", firstSection(sections, "sample code", "code"))
	if err != nil {
		return nil, err
	}
	obsRaw := firstSection(sections, "observations json array", "observations json", "observations")
	domains := parseDomains(firstSection(sections, "domains (optional scope filter)", "domains"))
	if !allowEmpty && strings.TrimSpace(tech) == "" && strings.TrimSpace(code) == "" && strings.TrimSpace(obsRaw) == "" {
		return nil, &Error{Msg: "provide tech spec and/or sample code (or full package JSON / observations / pull request)"}
	}
	var observations []any
	if strings.TrimSpace(obsRaw) != "" {
		if err := json.Unmarshal([]byte(obsRaw), &observations); err != nil {
			return nil, &Error{Msg: fmt.Sprintf("observations JSON is invalid: %v", err)}
		}
	}
	pkg := map[string]any{
		"schema_version": "pathfinder-evidence-package-v1",
		"package_id":     fmt.Sprintf("github-issue-%d", issueNumber),
		"scope":          map[string]any{},
		"observations":   []any{},
	}
	if len(domains) > 0 {
		domAny := make([]any, len(domains))
		for i, d := range domains {
			domAny[i] = d
		}
		pkg["scope"] = map[string]any{"domains": domAny}
	}
	var techSHA string
	if tech != "" {
		techSHA = sha(tech)
		pkg["tech_spec"] = map[string]any{
			"artifact_id": "tech_spec",
			"path":        "issue/tech-spec.md",
			"revision":    "sha256:" + techSHA,
			"sha256":      techSHA,
			"content":     tech,
		}
	}
	if code != "" {
		codeSHA := sha(code)
		pkg["code"] = []any{map[string]any{
			"artifact_id": "code-0",
			"path":        guessCodePath(code),
			"revision":    "sha256:" + codeSHA,
			"sha256":      codeSHA,
			"content":     code,
		}}
	}
	obsOut := []any{}
	for index, item := range observations {
		obs, ok := item.(map[string]any)
		if !ok {
			return nil, &Error{Msg: fmt.Sprintf("observations[%d] must be an object", index)}
		}
		obs = cloneMap(obs)
		if _, ok := obs["artifact_id"]; !ok {
			if tech != "" {
				obs["artifact_id"] = "tech_spec"
			} else {
				obs["artifact_id"] = "code-0"
			}
		}
		if _, ok := obs["path"]; !ok {
			if obs["artifact_id"] == "tech_spec" {
				obs["path"] = "issue/tech-spec.md"
			} else if codeList, ok := pkg["code"].([]any); ok && len(codeList) > 0 {
				obs["path"] = codeList[0].(map[string]any)["path"]
			} else {
				obs["path"] = "issue/sample-code.txt"
			}
		}
		if _, hasRev := obs["revision"]; !hasRev {
			if _, hasSHA := obs["source_sha256"]; !hasSHA {
				if obs["artifact_id"] == "tech_spec" && techSHA != "" {
					obs["revision"] = "sha256:" + techSHA
					obs["source_sha256"] = techSHA
				} else if codeList, ok := pkg["code"].([]any); ok && len(codeList) > 0 {
					c0 := codeList[0].(map[string]any)
					obs["revision"] = c0["revision"]
					obs["source_sha256"] = c0["sha256"]
				} else {
					return nil, &Error{Msg: fmt.Sprintf("observations[%d] needs source_sha256/revision when no tech_spec/code content is supplied", index)}
				}
			}
		}
		if _, ok := obs["locator"]; !ok {
			pred := obs["predicate"]
			if pred == nil {
				pred = fmt.Sprintf("obs-%d", index)
			}
			obs["locator"] = map[string]any{"kind": "issue_claim", "value": pred}
		}
		obsOut = append(obsOut, obs)
	}
	pkg["observations"] = obsOut
	return pkg, nil
}

func pinArtifactHashes(packageObj map[string]any) map[string]any {
	out := cloneMap(packageObj)
	digests := map[string]string{}
	if tech, ok := out["tech_spec"].(map[string]any); ok {
		if content, ok := tech["content"].(string); ok && strings.TrimSpace(content) != "" {
			tech = cloneMap(tech)
			digest := sha(content)
			tech["sha256"] = digest
			tech["revision"] = "sha256:" + digest
			if _, ok := tech["artifact_id"]; !ok {
				tech["artifact_id"] = "tech_spec"
			}
			if _, ok := tech["path"]; !ok {
				tech["path"] = "issue/tech-spec.md"
			}
			out["tech_spec"] = tech
			digests[tech["artifact_id"].(string)] = digest
		}
	}
	var codeBlocks []any
	for index, raw := range asSlice(out["code"]) {
		block, ok := raw.(map[string]any)
		if !ok {
			codeBlocks = append(codeBlocks, raw)
			continue
		}
		content, ok := block["content"].(string)
		if !ok {
			codeBlocks = append(codeBlocks, block)
			continue
		}
		item := cloneMap(block)
		digest := sha(content)
		item["sha256"] = digest
		item["revision"] = "sha256:" + digest
		if _, ok := item["artifact_id"]; !ok {
			item["artifact_id"] = fmt.Sprintf("code-%d", index)
		}
		if _, ok := item["path"]; !ok {
			item["path"] = fmt.Sprintf("issue/sample-code-%d.txt", index)
		}
		codeBlocks = append(codeBlocks, item)
		digests[item["artifact_id"].(string)] = digest
	}
	if len(codeBlocks) > 0 {
		out["code"] = codeBlocks
	}
	var observations []any
	for _, raw := range asSlice(out["observations"]) {
		item, ok := raw.(map[string]any)
		if !ok {
			observations = append(observations, raw)
			continue
		}
		obs := cloneMap(item)
		if id, ok := obs["artifact_id"].(string); ok {
			if digest, ok := digests[id]; ok {
				obs["source_sha256"] = digest
				obs["revision"] = "sha256:" + digest
			}
		}
		observations = append(observations, obs)
	}
	if _, ok := out["observations"]; ok {
		out["observations"] = observations
	}
	return out
}

// PackageFromIssue builds a pinned package; catalogDir is retained for caller compatibility.
func PackageFromIssue(body string, issueNumber int, catalogDir string, subjects map[string]string, reg *predicates.Registry, opts Options) (map[string]any, error) {
	sections := ParseFormSections(body)
	if !AttestationAccepted(body, sections) {
		return nil, &Error{Msg: "public/synthetic attestation checkbox is required"}
	}
	pkg, err := extractPackageJSON(body, sections)
	if err != nil {
		return nil, err
	}
	if pkg == nil {
		prText := firstSection(sections,
			"same-repo pull request (optional)",
			"same-repo pull request",
			"pull request",
			"pr",
		)
		var prPkg map[string]any
		if strings.TrimSpace(prText) != "" {
			if opts.PRClient == nil || strings.TrimSpace(opts.Repo) == "" {
				return nil, &Error{Msg: "pull request adapter requires repository context"}
			}
			res, rerr := pr.Resolve(opts.PRClient, opts.Repo, prText, issueNumber)
			if rerr != nil {
				return nil, &Error{Msg: rerr.Error()}
			}
			prPkg = res.Package
		}
		fieldPkg, ferr := buildPackageFromFields(sections, issueNumber, prPkg != nil)
		if ferr != nil {
			return nil, ferr
		}
		if prPkg != nil {
			pkg = mergePRAndFields(prPkg, fieldPkg)
		} else {
			pkg = fieldPkg
		}
	}
	pkg = cloneMap(pkg)
	if _, ok := pkg["package_id"]; !ok {
		pkg["package_id"] = fmt.Sprintf("github-issue-%d", issueNumber)
	}
	if pkg["schema_version"] != "pathfinder-evidence-package-v1" {
		return nil, &Error{Msg: "package schema_version must be pathfinder-evidence-package-v1"}
	}
	pkg = pinArtifactHashes(pkg)
	// Keep raw pinned artifacts intact until the evaluation boundary chooses its
	// extractor. This lets explicit semantic extraction run before heuristics.
	if _, ok := pkg["observations"]; !ok {
		pkg["observations"] = []any{}
	}
	if _, err := pkgcollect.CollectObservations(pkg, reg); err != nil {
		return nil, err
	}
	_ = catalogDir
	return pkg, nil
}

func mergePRAndFields(prPkg, fieldPkg map[string]any) map[string]any {
	out := cloneMap(prPkg)
	if tech, ok := fieldPkg["tech_spec"].(map[string]any); ok {
		out["tech_spec"] = tech
	}
	code := asSlice(out["code"])
	for _, raw := range asSlice(fieldPkg["code"]) {
		code = append(code, raw)
	}
	if len(code) > 0 {
		out["code"] = code
	}
	if scope, ok := fieldPkg["scope"].(map[string]any); ok {
		if domains, ok := scope["domains"].([]any); ok && len(domains) > 0 {
			out["scope"] = scope
		}
	}
	if obs := asSlice(fieldPkg["observations"]); len(obs) > 0 {
		out["observations"] = obs
	}
	return out
}

// RenderResultComment builds markdown without embedding source bodies.
func RenderResultComment(report, packageObj map[string]any, runURL string) (string, error) {
	counts := countMap(report["counts"])
	lines := []string{
		CommentMarker,
		"## Pathfinder catalog evaluation",
		"",
		fmt.Sprintf("- **Aggregate status:** `%v`", report["aggregate_status"]),
		fmt.Sprintf("- **Meaning:** %v", report["aggregate_meaning"]),
		fmt.Sprintf("- **Catalog size:** %v", report["catalog_size"]),
		fmt.Sprintf("- **Observations used:** %v", report["observation_count"]),
		fmt.Sprintf("- **Package id:** `%v`", packageObj["package_id"]),
		fmt.Sprintf("- **Report fingerprint:** `%v`", report["report_sha256"]),
		fmt.Sprintf("- **Workflow run:** %s", runURL),
	}
	if cat, ok := report["catalog"].(map[string]any); ok {
		lines = append(lines,
			fmt.Sprintf("- **Catalog:** `%v` (`%v`) v`%v`", cat["catalog_id"], cat["mode"], cat["version"]),
			fmt.Sprintf("- **Catalog manifest:** `%v`", cat["manifest_sha256"]),
		)
	}
	if v, ok := report["in_scope_count"]; ok {
		lines = append(lines, fmt.Sprintf("- **In-scope requirements:** %v / %v", v, report["catalog_size"]))
	}
	if v, ok := report["result_count"]; ok {
		lines = append(lines, fmt.Sprintf("- **Requirement evaluations:** %v (all accepted evidence is evaluated together)", v))
	}
	if roleCounts, ok := report["evidence_role_counts"].(map[string]int); ok && len(roleCounts) > 0 {
		lines = append(lines, fmt.Sprintf("- **Evidence sources:** %v", roleCounts))
	}
	extraction, _ := report["extraction"].(map[string]any)
	if extraction == nil {
		extraction, _ = packageObj["extraction"].(map[string]any)
	}
	if extraction != nil {
		lines = append(lines, fmt.Sprintf(
			"- **Evidence extraction:** `%v` (status `%v`, %v accepted observations)",
			extraction["extractor"], extraction["status"], extraction["observation_count"],
		))
		if extraction["input_tokens"] != nil || extraction["output_tokens"] != nil {
			lines = append(lines, fmt.Sprintf("- **Semantic model usage:** %v input / %v output tokens; at most one generation call", extraction["input_tokens"], extraction["output_tokens"]))
		}
	}
	scope, _ := packageObj["scope"].(map[string]any)
	if scope == nil || len(asSlice(scope["domains"])) == 0 {
		lines = append(lines, "- **Domain filter:** none (all active catalog domains evaluated)")
	} else {
		lines = append(lines, fmt.Sprintf("- **Domain filter:** %v", scope["domains"]))
	}
	if adapter, ok := packageObj["adapter"].(map[string]any); ok {
		lines = append(lines, fmt.Sprintf("- **Input adapter:** `%v`", adapter["kind"]))
		if n, ok := adapter["pr_number"]; ok {
			lines = append(lines, fmt.Sprintf("- **Pull request:** `#%v` @ `%v`", n, adapter["head_sha"]))
		}
		if n, ok := adapter["file_count"]; ok {
			lines = append(lines, fmt.Sprintf("- **PR files packed:** %v", n))
		}
		if lims, ok := adapter["limitations"].([]any); ok && len(lims) > 0 {
			lines = append(lines, fmt.Sprintf("- **Adapter limitations:** %d (see package artifact)", len(lims)))
		} else if lims, ok := adapter["limitations"].([]string); ok && len(lims) > 0 {
			lines = append(lines, fmt.Sprintf("- **Adapter limitations:** %d (see package artifact)", len(lims)))
		}
	}
	lines = append(lines,
		"",
		"### Outcome counts",
		"",
		"| Outcome | Count |",
		"|---|---:|",
		fmt.Sprintf("| supported_deviation | %d |", counts["supported_deviation"]),
		fmt.Sprintf("| no_deviation_found | %d |", counts["no_deviation_found"]),
		fmt.Sprintf("| inconclusive | %d |", counts["inconclusive"]),
		fmt.Sprintf("| not_applicable | %d |", counts["not_applicable"]),
		"",
		"### Notable requirements",
		"",
	)
	results, _ := report["results"].([]map[string]any)
	if results == nil {
		if raw, ok := report["results"].([]any); ok {
			for _, r := range raw {
				if m, ok := r.(map[string]any); ok {
					results = append(results, m)
				}
			}
		}
	}
	var notable []map[string]any
	for _, row := range results {
		o := row["outcome"]
		if o == "supported_deviation" || o == "no_deviation_found" || row["relationship"] == "conflicting_evidence" {
			notable = append(notable, row)
			if len(notable) >= 20 {
				break
			}
		}
	}
	if len(notable) == 0 {
		lines = append(lines, "_No confident aligned/deviation results; most in-scope requirements were inconclusive or out of scope._")
	} else {
		lines = append(lines, "| ADR | Domain | Outcome | Predicate | Evidence sources |", "|---|---|---|---|---|")
		for _, row := range notable {
			outcome := fmt.Sprint(row["outcome"])
			if row["relationship"] == "conflicting_evidence" {
				outcome += " (conflicting evidence)"
			}
			lines = append(lines, fmt.Sprintf("| `%v` | %v | `%v` | `%v` | %s |", row["adr_id"], row["domain"], outcome, row["predicate"], escapeTableCell(provenanceSummary(row["provenance"]))))
		}
	}
	lines = append(lines,
		"",
		"### Evidence boundary",
		"",
		"- Full tech-spec/code bodies are **not** copied into this comment.",
		"- Download the workflow artifact `pathfinder-issue-evaluation` for the full report JSON.",
		"### How to read this",
		"",
		"- Unextracted predicates stay `inconclusive` — silence is not compliance.",
		"- `not_applicable` means out of scope (domain/lifecycle), not aligned.",
		"- Catalog labels are advisory (`prototype_corpus_unadjudicated` / synthetic). Findings do not block merges.",
		"- Full report JSON is in the workflow artifact (`pathfinder-issue-evaluation-*`, retained ~14 days).",
		"- Lean job index: `pathfinder-jobs` branch → `jobs/jobs.jsonl`. Re-run via Actions workflow_dispatch.",
		"- First-run guide: `docs/PATHFINDER_FIRST_RUN.md`.",
		"",
	)
	comment := strings.Join(lines, "\n")
	if tech, ok := packageObj["tech_spec"].(map[string]any); ok {
		if c, ok := tech["content"].(string); ok && len(c) > 40 && strings.Contains(comment, c) {
			return "", &Error{Msg: "refusing to post a comment that embeds source content"}
		}
	}
	for _, raw := range asSlice(packageObj["code"]) {
		if block, ok := raw.(map[string]any); ok {
			if c, ok := block["content"].(string); ok && len(c) > 40 && strings.Contains(comment, c) {
				return "", &Error{Msg: "refusing to post a comment that embeds source content"}
			}
		}
	}
	return comment, nil
}

func provenanceSummary(value any) string {
	var refs []map[string]any
	switch xs := value.(type) {
	case []map[string]any:
		refs = xs
	case []any:
		for _, raw := range xs {
			if ref, ok := raw.(map[string]any); ok {
				refs = append(refs, ref)
			}
		}
	}
	seen := map[string]bool{}
	parts := []string{}
	for _, ref := range refs {
		role, _ := ref["evidence_role"].(string)
		path, _ := ref["path"].(string)
		if role == "" {
			role = "source"
		}
		part := role
		if path != "" {
			path = strings.ReplaceAll(strings.ReplaceAll(path, "\r", " "), "\n", " ")
			path = strings.ReplaceAll(html.EscapeString(path), "|", "&#124;")
			part += ": <code>" + path + "</code>"
		}
		if !seen[part] {
			seen[part] = true
			parts = append(parts, part)
		}
	}
	if len(parts) == 0 {
		return "see report artifact"
	}
	return strings.Join(parts, "; ")
}

func escapeTableCell(value string) string {
	return strings.ReplaceAll(strings.ReplaceAll(strings.ReplaceAll(value, "|", "\\|"), "\r", " "), "\n", " ")
}

func RenderErrorComment(message, runURL string) string {
	return CommentMarker + "\n" +
		"## Pathfinder catalog evaluation failed\n\n" +
		message + "\n\n" +
		"Workflow run: " + runURL + "\n\n" +
		"Fix the issue body (attestation, package schema, or paste content) and edit the issue to re-run.\n" +
		"See `docs/ISSUE_ANALYZE_WORKFLOW.md`.\n"
}

func firstSection(sections map[string]string, keys ...string) string {
	for _, k := range keys {
		if v, ok := sections[k]; ok {
			return v
		}
	}
	return ""
}

func parseDomains(raw string) []string {
	raw = strings.ReplaceAll(raw, "\n", ",")
	var out []string
	for _, part := range strings.Split(raw, ",") {
		part = strings.TrimSpace(part)
		if part != "" {
			out = append(out, part)
		}
	}
	return out
}

// CatalogModeFromIssueBody reads an optional Catalog pack section (real|synthetic).
// Empty means caller should use the process default (real).
func CatalogModeFromIssueBody(body string) string {
	sections := ParseFormSections(body)
	raw := strings.ToLower(strings.TrimSpace(firstSection(sections, "catalog pack", "catalog mode", "catalog")))
	if raw == "" {
		return ""
	}
	// GitHub dropdown / radio lines often look like: "Real prototype pack (default)"
	switch {
	case strings.Contains(raw, "synthetic"):
		return "synthetic"
	case strings.Contains(raw, "real"):
		return "real"
	default:
		return ""
	}
}

func cloneMap(in map[string]any) map[string]any {
	out := make(map[string]any, len(in))
	for k, v := range in {
		out[k] = v
	}
	return out
}

func asSlice(v any) []any {
	if v == nil {
		return nil
	}
	if s, ok := v.([]any); ok {
		return s
	}
	return nil
}

func countMap(v any) map[string]int {
	out := map[string]int{
		"supported_deviation": 0,
		"no_deviation_found":  0,
		"inconclusive":        0,
		"not_applicable":      0,
	}
	switch m := v.(type) {
	case map[string]int:
		for k, n := range m {
			out[k] = n
		}
	case map[string]any:
		for k, raw := range m {
			switch n := raw.(type) {
			case int:
				out[k] = n
			case float64:
				out[k] = int(n)
			}
		}
	}
	return out
}
