// Package paste extracts sparse, provenance-bound observations from pasted
// technical specifications and source snippets.
package paste

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

const (
	ExtractorID      = "paste_heuristic_v1"
	ExtractorVersion = "paste-heuristic-v2"
)

var trueOnlyPredicates = map[string]struct{}{
	"security.secret_in_source.present":     {},
	"privacy.sensitive_log.present":         {},
	"frontend.secret_in_bundle.present":     {},
	"messaging.event.raw_gov_id":            {},
	"cicd.image.latest_tag":                 {},
	"cloud.security_group.ssh_open":         {},
	"cloud.iam.admin_equivalent":            {},
	"cloud.object_storage.public_read":      {},
	"ml.agent.unrestricted_shell":           {},
	"network.ssh.public_exposure":           {},
	"supply_chain.dependency.legacy_crypto": {},
}

type artifact struct {
	id, path, revision, digest, content, language string
}

type rule struct {
	predicate string
	re        *regexp.Regexp
	value     any
}

var (
	secretAssignmentRE = regexp.MustCompile(`(?i)(api[_-]?key|secret|password|token|private[_-]?key|access[_-]?key)\s*[=:]\s*["'][^"']{8,}["']`)
	secretTokenRE      = regexp.MustCompile(`["'](sk[-_](live|test)[-_][A-Za-z0-9]{8,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,})["']`)
	sensitiveLogRE     = regexp.MustCompile(`(?i)\b(log|logger|print|fmt\.Print|slog)\w*\s*\([^)]*\b(pan|ssn|social\s+security|credit\s+card|cvv|password)\b`)
	tlsPolicyRE        = regexp.MustCompile(`(?i)\b(tls-1-2-strict|tls-1-3-only|legacy-ssl)\b`)
	licenseRE          = regexp.MustCompile(`\b(Apache-2\.0|MIT|BSD-3-Clause)\b`)
)

// EnsureObservations returns a shallow package copy. Existing non-empty
// observations are preserved without requiring subjects; otherwise extraction
// is attempted and subjects must be supplied by the caller.
func EnsureObservations(pkg map[string]any, subjects map[string]string) (map[string]any, error) {
	out := cloneMap(pkg)
	if existing, ok := out["observations"].([]any); ok && len(existing) > 0 {
		return out, nil
	}
	// Accommodate programmatically built packages that use []map[string]any.
	if existing, ok := out["observations"].([]map[string]any); ok && len(existing) > 0 {
		return out, nil
	}
	observations, err := ExtractObservations(out, subjects)
	if err != nil {
		return nil, err
	}
	out["observations"] = observations
	out["extraction"] = map[string]any{
		"extractor":         ExtractorID,
		"extractor_version": ExtractorVersion,
		"observation_count": len(observations),
	}
	return out, nil
}

// ExtractObservations deterministically extracts allowlisted observations.
// It returns an error rather than emitting subjectless evidence.
func ExtractObservations(pkg map[string]any, subjects map[string]string) ([]any, error) {
	if len(subjects) == 0 {
		return nil, fmt.Errorf("paste extraction requires predicate subjects")
	}
	var candidates []map[string]any
	for _, a := range artifactsFromPackage(pkg) {
		switch a.language {
		case "markdown":
			candidates = append(candidates, extractMarkdown(a, subjects)...)
			candidates = append(candidates, extractKubernetesYAML(a, subjects)...)
			candidates = append(candidates, extractSecrets(a, subjects)...)
		case "yaml":
			candidates = append(candidates, extractKubernetesYAML(a, subjects)...)
			candidates = append(candidates, extractMarkdown(a, subjects)...)
			candidates = append(candidates, extractSecrets(a, subjects)...)
		case "python":
			candidates = append(candidates, extractPython(a, subjects)...)
		case "go":
			candidates = append(candidates, extractGo(a, subjects)...)
		case "json":
			candidates = append(candidates, extractJSON(a, subjects)...)
			candidates = append(candidates, extractSecrets(a, subjects)...)
		default:
			candidates = append(candidates, extractMarkdown(a, subjects)...)
			candidates = append(candidates, extractKubernetesYAML(a, subjects)...)
			candidates = append(candidates, extractSecrets(a, subjects)...)
		}
	}
	resolved := resolveConflicts(candidates)
	out := make([]any, len(resolved))
	for i := range resolved {
		out[i] = resolved[i]
	}
	return out, nil
}

func artifactsFromPackage(pkg map[string]any) []artifact {
	var out []artifact
	if tech, ok := asMap(pkg["tech_spec"]); ok {
		if content, ok := tech["content"].(string); ok && strings.TrimSpace(content) != "" {
			out = append(out, makeArtifact(tech, content, "tech_spec", "issue/tech-spec.md", "markdown"))
		}
	}
	code, _ := pkg["code"].([]any)
	if maps, ok := pkg["code"].([]map[string]any); ok {
		code = make([]any, len(maps))
		for i := range maps {
			code[i] = maps[i]
		}
	}
	for i, raw := range code {
		block, ok := asMap(raw)
		if !ok {
			continue
		}
		content, ok := block["content"].(string)
		if !ok || strings.TrimSpace(content) == "" {
			continue
		}
		path := stringValue(block["path"], fmt.Sprintf("issue/sample-code-%d.txt", i))
		out = append(out, makeArtifact(block, content, fmt.Sprintf("code-%d", i), path, detectLanguage(path, content)))
	}
	return out
}

func makeArtifact(raw map[string]any, content, defaultID, defaultPath, language string) artifact {
	digest := stringValue(raw["sha256"], sha(content))
	return artifact{
		id:       stringValue(raw["artifact_id"], defaultID),
		path:     stringValue(raw["path"], defaultPath),
		revision: stringValue(raw["revision"], "sha256:"+digest),
		digest:   digest,
		content:  content,
		language: language,
	}
}

func detectLanguage(path, content string) string {
	lower := strings.ToLower(path)
	switch {
	case strings.HasSuffix(lower, ".py"):
		return "python"
	case strings.HasSuffix(lower, ".go"):
		return "go"
	case strings.HasSuffix(lower, ".yaml"), strings.HasSuffix(lower, ".yml"):
		return "yaml"
	case strings.HasSuffix(lower, ".md"), strings.HasSuffix(lower, ".markdown"), strings.HasSuffix(lower, ".txt"):
		return "markdown"
	case strings.Contains(content, "package main"), regexp.MustCompile(`\bfunc\s+\w+\s*\(`).MatchString(content):
		return "go"
	case regexp.MustCompile(`(?m)^\s*(def|class|import|from)\s+`).MatchString(content), strings.Contains(content, "async def"):
		return "python"
	case strings.HasPrefix(strings.TrimSpace(content), "{"), strings.HasPrefix(strings.TrimSpace(content), "["):
		return "json"
	case regexp.MustCompile(`(?m)^(apiVersion|kind):\s*\S+`).MatchString(content) && regexp.MustCompile(`(?m)^metadata:\s*$`).MatchString(content):
		return "yaml"
	default:
		return "markdown"
	}
}

func candidate(predicate string, value any, a artifact, start, end int, subjects map[string]string, prefix string) map[string]any {
	subject := subjects[predicate]
	if subject == "" {
		return nil
	}
	if _, trueOnly := trueOnlyPredicates[predicate]; trueOnly && value != true {
		return nil
	}
	if start < 0 || end < start || end > len(a.content) {
		return nil
	}
	return map[string]any{
		"evidence_id":   fmt.Sprintf("%s-%s-%d", prefix, strings.ReplaceAll(predicate, ".", "_"), start),
		"predicate":     predicate,
		"subject":       subject,
		"value":         value,
		"artifact_id":   a.id,
		"revision":      a.revision,
		"path":          a.path,
		"source_sha256": a.digest,
		"locator":       lineSpan(a.content, start, end),
	}
}

func lineSpan(text string, start, end int) map[string]any {
	return map[string]any{
		"kind":              "paste_span",
		"line":              strings.Count(text[:start], "\n") + 1,
		"start":             start,
		"end":               end,
		"excerpt_sha256":    sha(text[start:end]),
		"extractor":         ExtractorID,
		"extractor_version": ExtractorVersion,
	}
}

func extractSecrets(a artifact, subjects map[string]string) []map[string]any {
	var out []map[string]any
	for _, re := range []*regexp.Regexp{secretAssignmentRE, secretTokenRE} {
		for _, loc := range re.FindAllStringIndex(a.content, -1) {
			if item := candidate("security.secret_in_source.present", true, a, loc[0], loc[1], subjects, "EXT-sec"); item != nil {
				out = append(out, item)
			}
		}
	}
	for _, loc := range sensitiveLogRE.FindAllStringIndex(a.content, -1) {
		if item := candidate("privacy.sensitive_log.present", true, a, loc[0], loc[1], subjects, "EXT-pii"); item != nil {
			out = append(out, item)
		}
	}
	return out
}

func extractMarkdown(a artifact, subjects map[string]string) []map[string]any {
	var out []map[string]any
	addMatches := func(predicate string, re *regexp.Regexp, value func([]string) (any, bool)) {
		for _, loc := range re.FindAllStringSubmatchIndex(a.content, -1) {
			groups := submatches(a.content, loc)
			v, ok := value(groups)
			if !ok {
				continue
			}
			if item := candidate(predicate, v, a, loc[0], loc[1], subjects, "EXT-md"); item != nil {
				out = append(out, item)
			}
		}
	}
	for _, pattern := range []string{
		`(?i)sessions?\s+(expire|ttl|lifetime|timeout)\w*\s*(after|of|:)?\s*(\d+(\.\d+)?)\s*(seconds?|minutes?|hours?|days?)`,
		`(?i)(absolute\s+)?(session\s+)?ttl\s*(of|=|:)?\s*(\d+(\.\d+)?)\s*(seconds?|minutes?|hours?|days?)`,
		`(?i)session(s)?\s+(are\s+)?valid\s+for\s+(\d+(\.\d+)?)\s*(seconds?|minutes?|hours?|days?)`,
	} {
		re := regexp.MustCompile(pattern)
		for _, loc := range re.FindAllStringSubmatchIndex(a.content, -1) {
			g := submatches(a.content, loc)
			if len(g) < 3 {
				continue
			}
			amount, unit := lastNumberAndUnit(g)
			n, err := strconv.ParseFloat(amount, 64)
			seconds, ok := toSeconds(n, unit)
			if err == nil && ok {
				if item := candidate("session.ttl_seconds", seconds, a, loc[0], loc[1], subjects, "EXT-md"); item != nil {
					out = append(out, item)
				}
			}
		}
	}
	addMatches("session.idle_timeout_seconds", regexp.MustCompile(`(?i)idle\s+(session\s+)?(timeout|expire\w*)\s*(after|of|:)?\s*(\d+(\.\d+)?)\s*(seconds?|minutes?|hours?|days?)`), func(g []string) (any, bool) {
		amount, unit := lastNumberAndUnit(g)
		n, err := strconv.ParseFloat(amount, 64)
		if err != nil {
			return nil, false
		}
		seconds, ok := toSeconds(n, unit)
		return seconds, ok
	})
	numeric := []struct{ predicate, pattern string }{
		{"kubernetes.deployment.replicas", `(?i)\breplicas?\s*[:=]\s*(\d+)\b`},
		{"kubernetes.deployment.replicas", `(?i)\b(run|deploy(ed|ment)?)\s+(with\s+)?(\d+)\s+replicas?\b`},
		{"messaging.consumer.max_retries", `(?i)\b(max(imum)?\s+)?retries?\s*[:=]\s*(\d+)\b`},
		{"messaging.consumer.max_retries", `(?i)\bconsumer\s+max\s+retries?\s*[:=]?\s*(\d+)\b`},
		{"identity.password.min_length", `(?i)\bpassword\s+(minimum\s+)?(length|min)\s*[:=]?\s*(\d+)\b`},
		{"observability.logging.retention_days", `(?i)\blog(ging)?\s+retention\s*[:=]?\s*(\d+)\s*days?\b`},
		{"privacy.data_retention_days", `(?i)\bdata\s+retention\s*[:=]?\s*(\d+)\s*days?\b`},
		{"compliance.audit_log.retention_days", `(?i)\baudit\s+log\s+retention\s*[:=]?\s*(\d+)\s*days?\b`},
		{"data.backup.retention_days", `(?i)\bbackup\s+retention\s*[:=]?\s*(\d+)\s*days?\b`},
		{"storage.snapshot.retention_days", `(?i)\bsnapshot\s+retention\s*[:=]?\s*(\d+)\s*days?\b`},
		{"security.certificate.validity_days", `(?i)\bcertificate\s+validity\s*[:=]?\s*(\d+)\s*days?\b`},
		{"ml.training_data.retention_days", `(?i)\btraining\s+data\s+retention\s*[:=]?\s*(\d+)\s*days?\b`},
		{"kubernetes.pod_disruption_budget.max_unavailable", `(?i)\bmaxUnavailable\s*[:=]\s*(\d+)\b`},
		{"kubernetes.pod_disruption_budget.min_available", `(?i)\bminAvailable\s*[:=]\s*(\d+)\b`},
		{"cicd.branch_protection.required_reviews", `(?i)\brequired\s+reviews?\s*[:=]?\s*(\d+)\b`},
	}
	for _, r := range numeric {
		re := regexp.MustCompile(r.pattern)
		for _, loc := range re.FindAllStringSubmatchIndex(a.content, -1) {
			g := submatches(a.content, loc)
			n, err := strconv.Atoi(lastNumeric(g))
			if err == nil {
				if item := candidate(r.predicate, n, a, loc[0], loc[1], subjects, "EXT-md"); item != nil {
					out = append(out, item)
				}
			}
		}
	}

	trueRules := []rule{
		boolRule("security.encryption_at_rest.enabled", `(?i)\bencryption\s+at\s+rest\s+(is\s+)?(enabled|on|required)\b`),
		boolRule("security.encryption_at_rest.enabled", `(?i)\benable(s|d)?\s+encryption\s+at\s+rest\b`),
		boolRule("storage.volume.encryption_enabled", `(?i)\bvolume\s+encryption\s+(is\s+)?(enabled|on|required)\b`),
		boolRule("data.backup.encryption_enabled", `(?i)\bbackup\s+encryption\s+(is\s+)?(enabled|on|required)\b`),
		boolRule("kubernetes.readiness_probe.present", `(?i)\breadiness\s+probe\s+(is\s+)?(configured|present|enabled)\b`),
		boolRule("kubernetes.liveness_probe.present", `(?i)\bliveness\s+probe\s+(is\s+)?(configured|present|enabled)\b`),
		boolRule("kubernetes.pod_disruption_budget.present", `(?i)\b(pod\s+disruption\s+budget|PDB)\s+(is\s+)?(configured|present|required|defined)\b`),
		boolRule("kubernetes.hpa.present", `(?i)\b(horizontal\s+pod\s+autoscaler|HPA)\s+(is\s+)?(configured|present|enabled)\b`),
		boolRule("kubernetes.network_policy.present", `(?i)\bnetwork\s+polic(y|ies)\s+(is|are)\s+(configured|present|enabled)\b`),
		boolRule("kubernetes.ingress.tls_enabled", `(?i)\bingress\s+tls\s+(is\s+)?(enabled|required|terminated)\b`),
		boolRule("messaging.dlq.present", `(?i)\b(dead[- ]letter\s+queue|DLQ)\s+(is\s+)?(configured|present|enabled|used)\b`),
		boolRule("messaging.outbox.present", `(?i)\boutbox\s+(pattern\s+)?(is\s+)?(used|present|configured)\b`),
		boolRule("messaging.consumer.idempotent", `(?i)\b(consumers?\s+are\s+idempotent|idempotent\s+consumers?)\b`),
		boolRule("messaging.schema_registry.used", `(?i)\bschema\s+registry\s+(is\s+)?(used|required|enabled)\b`),
		boolRule("api.rate_limit.enabled", `(?i)\brate\s+limit(ing)?\s+(is\s+)?(enabled|enforced|required)\b`),
		boolRule("api.auth_middleware.present", `(?i)\b(auth(entication)?\s+middleware|all\s+routes\s+require\s+auth)\b`),
		boolRule("api.input_validation.present", `(?i)\b(request|input)\s+validation\s+(is\s+)?(enabled|required|enforced)\b`),
		boolRule("api.pagination.present", `(?i)\b(list\s+)?(endpoints?\s+)?paginat(e|ion)\b`),
		boolRule("api.openapi.published", `(?i)\bopenapi\s+(spec|document)?\s+(is\s+)?(published|available)\b`),
		boolRule("api.request_id.propagated", `(?i)\brequest[- ]id\s+(is\s+)?(propagated|required)\b`),
		boolRule("identity.mfa.required", `(?i)\b(mfa|multi[- ]factor)\s+(is\s+)?(required|enforced|mandatory)\b`),
		boolRule("identity.refresh_token.rotation_enabled", `(?i)\brefresh\s+tokens?\s+(use\s+)?rotation\b`),
		boolRule("session.server_enforced", `(?i)\bsessions?\s+(are\s+)?server[- ](side\s+)?enforced\b`),
		boolRule("security.hsts.enabled", `(?i)\bhsts\s+(is\s+)?(enabled|required)\b`),
		boolRule("security.waf.enabled", `(?i)\bwaf\s+(is\s+)?(enabled|required|deployed)\b`),
		boolRule("security.kms.rotation_enabled", `(?i)\bkms\s+(key\s+)?rotation\s+(is\s+)?(enabled|required)\b`),
		boolRule("observability.logging.structured_json", `(?i)\bstructured\s+json\s+log(ging|s)?\b`),
		boolRule("observability.logging.pii_scrubbing", `(?i)\b(pii|sensitive)\s+(scrubbing|redaction)\s+(is\s+)?(enabled|required)\b`),
		boolRule("observability.tracing.context_propagated", `(?i)\b(trace|tracing)\s+context\s+(is\s+)?propagated\b`),
		boolRule("observability.oncall.defined", `(?i)\bon[- ]call\s+(rotation\s+)?(is\s+)?(defined|configured)\b`),
		boolRule("cicd.secret_scanning.enabled", `(?i)\bsecret\s+scanning\s+(is\s+)?(enabled|required)\b`),
		boolRule("cicd.branch_protection.deny_force_push", `(?i)\bforce\s+push(es)?\s+(are\s+)?denied\b`),
		boolRule("cicd.image.signed", `(?i)\b(container\s+)?images?\s+(are\s+)?signed\b`),
		boolRule("cicd.sbom.published", `(?i)\bsbom\s+(is\s+)?(published|required)\b`),
		boolRule("data.client.tls_required", `(?i)\b(database|datastore)\s+client\s+tls\s+(is\s+)?required\b`),
		boolRule("cloud.rds.public_access_disabled", `(?i)\b(rds|database)\s+public\s+access\s+(is\s+)?disabled\b`),
		boolRule("cloud.object_storage.versioning_enabled", `(?i)\b(bucket|object\s+storage)\s+versioning\s+(is\s+)?(enabled|on)\b`),
		boolRule("cloud.audit_trail.enabled", `(?i)\b(cloud\s+)?audit\s+trail\s+(is\s+)?(enabled|on)\b`),
		boolRule("cloud.root.mfa_enabled", `(?i)\broot\s+(user\s+)?mfa\s+(is\s+)?(enabled|required)\b`),
		boolRule("privacy.deletion_api.present", `(?i)\bdeletion\s+api\s+(is\s+)?(present|available|implemented)\b`),
		boolRule("privacy.consent.recorded", `(?i)\bconsent\s+(is\s+)?(recorded|captured|stored)\b`),
		boolRule("frontend.csp.present", `(?i)\bcontent[- ]security[- ]policy\s+(is\s+)?(present|configured|enabled)\b`),
		boolRule("frontend.cookie.secure_httponly", `(?i)\bcookies?\s+(are\s+)?(secure\s+and\s+)?httpOnly\b`),
		boolRule("network.mesh.mtls_required", `(?i)\bmTLS\s+(is\s+)?(required|enforced)\b`),
		boolRule("network.egress.allowlist_enabled", `(?i)\begress\s+allowlist\s+(is\s+)?(enabled|enforced)\b`),
		boolRule("platform.tenant_isolation.enforced", `(?i)\btenant\s+isolation\s+(is\s+)?(enforced|required)\b`),
		boolRule("supply_chain.dependencies.pinned", `(?i)\bdependencies\s+(are\s+)?pinned\b`),
	}
	falseRules := []rule{
		{predicate: "security.encryption_at_rest.enabled", re: regexp.MustCompile(`(?i)\bencryption\s+at\s+rest\s+(is\s+)?(disabled|off|not\s+enabled)\b`), value: false},
		{predicate: "api.rate_limit.enabled", re: regexp.MustCompile(`(?i)\brate\s+limit(ing)?\s+(is\s+)?(disabled|off|not\s+enforced)\b`), value: false},
		{predicate: "kubernetes.readiness_probe.present", re: regexp.MustCompile(`(?i)\bno\s+readiness\s+probe\b`), value: false},
		{predicate: "messaging.dlq.present", re: regexp.MustCompile(`(?i)\bno\s+(dead[- ]letter\s+queue|DLQ)\b`), value: false},
	}
	for _, r := range append(trueRules, falseRules...) {
		for _, loc := range r.re.FindAllStringIndex(a.content, -1) {
			if item := candidate(r.predicate, r.value, a, loc[0], loc[1], subjects, "EXT-md"); item != nil {
				out = append(out, item)
			}
		}
	}
	for _, loc := range tlsPolicyRE.FindAllStringSubmatchIndex(a.content, -1) {
		if item := candidate("security.tls_policy.id", strings.ToLower(a.content[loc[2]:loc[3]]), a, loc[0], loc[1], subjects, "EXT-md"); item != nil {
			out = append(out, item)
		}
	}
	for _, loc := range licenseRE.FindAllStringSubmatchIndex(a.content, -1) {
		if item := candidate("supply_chain.license.id", a.content[loc[2]:loc[3]], a, loc[0], loc[1], subjects, "EXT-md"); item != nil {
			out = append(out, item)
		}
	}
	sensitiveClaim := regexp.MustCompile(`(?i)\b(logs?\s+may\s+include|log(ging)?\s+(includes?|contains?))\b.{0,40}\b(pan|ssn|password|credit\s*card)\b`)
	for _, loc := range sensitiveClaim.FindAllStringIndex(a.content, -1) {
		if item := candidate("privacy.sensitive_log.present", true, a, loc[0], loc[1], subjects, "EXT-md"); item != nil {
			out = append(out, item)
		}
	}
	return out
}

func boolRule(predicate, pattern string) rule {
	return rule{predicate: predicate, re: regexp.MustCompile(pattern), value: true}
}

func extractKubernetesYAML(a artifact, subjects map[string]string) []map[string]any {
	text := a.content
	k8sSignal := regexp.MustCompile(`(?m)^(apiVersion|kind):\s*\S+`).MatchString(text) ||
		regexp.MustCompile(`(?m)^\s*(replicas|readinessProbe|livenessProbe|maxUnavailable|minAvailable):\s*`).MatchString(text) ||
		strings.Contains(text, "PodDisruptionBudget") || strings.Contains(text, "HorizontalPodAutoscaler")
	if !k8sSignal {
		return nil
	}
	var out []map[string]any
	add := func(predicate string, value any, loc []int) {
		if item := candidate(predicate, value, a, loc[0], loc[1], subjects, "EXT-yaml"); item != nil {
			out = append(out, item)
		}
	}
	for _, loc := range regexp.MustCompile(`(?m)^\s*replicas:\s*(\d+)\s*$`).FindAllStringSubmatchIndex(text, -1) {
		n, _ := strconv.Atoi(text[loc[2]:loc[3]])
		add("kubernetes.deployment.replicas", n, loc)
	}
	for _, spec := range []struct{ predicate, pattern string }{
		{"kubernetes.readiness_probe.present", `(?i)readinessProbe:`},
		{"kubernetes.liveness_probe.present", `(?i)livenessProbe:`},
		{"kubernetes.pod_disruption_budget.present", `(?i)PodDisruptionBudget`},
		{"kubernetes.hpa.present", `(?i)HorizontalPodAutoscaler`},
		{"kubernetes.network_policy.present", `(?i)NetworkPolicy`},
	} {
		if loc := regexp.MustCompile(spec.pattern).FindStringIndex(text); loc != nil {
			add(spec.predicate, true, loc)
		}
	}
	for _, spec := range []struct{ predicate, pattern string }{
		{"kubernetes.pod_disruption_budget.max_unavailable", `(?m)^\s*maxUnavailable:\s*(\d+)\s*$`},
		{"kubernetes.pod_disruption_budget.min_available", `(?m)^\s*minAvailable:\s*(\d+)\s*$`},
	} {
		re := regexp.MustCompile(spec.pattern)
		for _, loc := range re.FindAllStringSubmatchIndex(text, -1) {
			n, _ := strconv.Atoi(text[loc[2]:loc[3]])
			add(spec.predicate, n, loc)
		}
	}
	if regexp.MustCompile(`(?i)kind:\s*Ingress`).MatchString(text) {
		if loc := regexp.MustCompile(`(?i)tls:`).FindStringIndex(text); loc != nil {
			add("kubernetes.ingress.tls_enabled", true, loc)
		}
	}
	return out
}

func extractGo(a artifact, subjects map[string]string) []map[string]any {
	out := extractSecrets(a, subjects)
	durationRE := regexp.MustCompile(`(?i)(\d+)\s*\*\s*time\.(Second|Minute|Hour)`)
	for _, loc := range durationRE.FindAllStringSubmatchIndex(a.content, -1) {
		start := loc[0] - 120
		if start < 0 {
			start = 0
		}
		end := loc[1] + 40
		if end > len(a.content) {
			end = len(a.content)
		}
		if !regexp.MustCompile(`(?i)session|ttl|maxage|cookie`).MatchString(a.content[start:end]) {
			continue
		}
		n, _ := strconv.ParseFloat(a.content[loc[2]:loc[3]], 64)
		seconds, _ := toSeconds(n, a.content[loc[4]:loc[5]])
		if item := candidate("session.ttl_seconds", seconds, a, loc[0], loc[1], subjects, "EXT-go"); item != nil {
			out = append(out, item)
		}
	}
	bareRE := regexp.MustCompile(`(?im)(const|var)\s+\w*(Session|TTL|MaxAge)\w*\s*=\s*(\d+)\s*(;|//|/\*|$)`)
	for _, loc := range bareRE.FindAllStringSubmatchIndex(a.content, -1) {
		n, _ := strconv.Atoi(lastNumeric(submatches(a.content, loc)))
		if item := candidate("session.ttl_seconds", n, a, loc[0], loc[1], subjects, "EXT-go"); item != nil {
			out = append(out, item)
		}
	}
	for _, spec := range []struct{ predicate, pattern string }{
		{"api.auth_middleware.present", `(?i)Use\([^)]*Auth|middleware\.Auth|RequireAuth|authMiddleware`},
		{"api.rate_limit.enabled", `(?i)RateLimit|httprate|tollbooth`},
	} {
		if loc := regexp.MustCompile(spec.pattern).FindStringIndex(a.content); loc != nil {
			if item := candidate(spec.predicate, true, a, loc[0], loc[1], subjects, "EXT-go"); item != nil {
				out = append(out, item)
			}
		}
	}
	for _, item := range extractMarkdown(a, subjects) {
		switch item["predicate"] {
		case "session.ttl_seconds", "session.idle_timeout_seconds", "security.encryption_at_rest.enabled", "security.tls_policy.id":
			out = append(out, item)
		}
	}
	return out
}

// extractPython intentionally uses a lightweight lexical approximation rather
// than a Python AST dependency. It covers assignment, decorators, function
// names, calls, and the same prose subset used by the reference extractor.
func extractPython(a artifact, subjects map[string]string) []map[string]any {
	out := extractSecrets(a, subjects)
	numericAssign := regexp.MustCompile(`(?im)^\s*([A-Za-z_][A-Za-z0-9_.]*(ttl|session_lifetime|max_age)[A-Za-z0-9_.]*)\s*=\s*(\d+(?:\.\d+)?)\b`)
	for _, loc := range numericAssign.FindAllStringSubmatchIndex(a.content, -1) {
		n, err := strconv.ParseFloat(a.content[loc[6]:loc[7]], 64)
		if err == nil {
			if item := candidate("session.ttl_seconds", int(n), a, loc[0], loc[1], subjects, "EXT-py"); item != nil {
				out = append(out, item)
			}
		}
	}
	authRE := regexp.MustCompile(`(?im)(def|async\s+def)\s+\w*auth\w*middleware\w*\s*\(|@(.*middleware.*auth|.*auth.*middleware)|\b(add_middleware|middleware|auth\w*)\s*\([^)\n]*auth`)
	if loc := authRE.FindStringIndex(a.content); loc != nil {
		if item := candidate("api.auth_middleware.present", true, a, loc[0], loc[1], subjects, "EXT-py"); item != nil {
			out = append(out, item)
		}
	}
	rateRE := regexp.MustCompile(`(?i)@.*(ratelimit|rate_limit)|\b(ratelimit|rate_limit)\w*\s*\(`)
	if loc := rateRE.FindStringIndex(a.content); loc != nil {
		if item := candidate("api.rate_limit.enabled", true, a, loc[0], loc[1], subjects, "EXT-py"); item != nil {
			out = append(out, item)
		}
	}
	for _, item := range extractMarkdown(a, subjects) {
		switch item["predicate"] {
		case "session.ttl_seconds", "session.idle_timeout_seconds", "security.encryption_at_rest.enabled", "security.tls_policy.id":
			out = append(out, item)
		}
	}
	return out
}

func extractJSON(a artifact, subjects map[string]string) []map[string]any {
	decoder := json.NewDecoder(bytes.NewBufferString(a.content))
	decoder.UseNumber()
	var data any
	if err := decoder.Decode(&data); err != nil {
		return nil
	}
	root, ok := data.(map[string]any)
	if !ok {
		return nil
	}
	aliases := map[string][]string{
		"session.ttl_seconds":                 {"session_ttl_seconds", "ttl_seconds", "sessionTtlSeconds"},
		"security.encryption_at_rest.enabled": {"encryption_at_rest", "encryptionAtRest"},
		"security.tls_policy.id":              {"tls_policy", "tlsPolicy"},
		"kubernetes.deployment.replicas":      {"replicas"},
	}
	var out []map[string]any
	var walk func(any, string)
	walk = func(value any, path string) {
		obj, isObject := value.(map[string]any)
		if isObject {
			keys := make([]string, 0, len(obj))
			for key := range obj {
				keys = append(keys, key)
			}
			sort.Strings(keys)
			for _, key := range keys {
				child := obj[key]
				childPath := key
				if path != "" {
					childPath = path + "." + key
				}
				walk(child, childPath)
			}
			return
		}
		value = normalizeJSONNumber(value)
		switch value.(type) {
		case string, bool, int, float64:
		default:
			return
		}
		parts := strings.Split(path, ".")
		leaf := parts[len(parts)-1]
		for predicate, names := range aliases {
			if !contains(names, leaf) && !strings.HasSuffix(path, predicate) {
				continue
			}
			re := regexp.MustCompile(`"` + regexp.QuoteMeta(leaf) + `"\s*:`)
			if loc := re.FindStringIndex(a.content); loc != nil {
				if item := candidate(predicate, value, a, loc[0], loc[1], subjects, "EXT-json"); item != nil {
					out = append(out, item)
				}
			}
		}
	}
	walk(root, "")
	return out
}

func resolveConflicts(candidates []map[string]any) []map[string]any {
	groups := map[string][]map[string]any{}
	for _, item := range candidates {
		key := fmt.Sprint(item["predicate"]) + "\x00" + fmt.Sprint(item["subject"])
		groups[key] = append(groups[key], item)
	}
	keys := make([]string, 0, len(groups))
	for key := range groups {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	var out []map[string]any
	for _, key := range keys {
		group := groups[key]
		first, _ := json.Marshal(group[0]["value"])
		conflict := false
		for _, item := range group[1:] {
			next, _ := json.Marshal(item["value"])
			if !bytes.Equal(first, next) {
				conflict = true
				break
			}
		}
		if !conflict {
			out = append(out, group[0])
		}
	}
	seen := map[string]struct{}{}
	for i, item := range out {
		id := item["evidence_id"].(string)
		if _, exists := seen[id]; exists {
			id = fmt.Sprintf("%s-%d", id, i)
			item["evidence_id"] = id
		}
		seen[id] = struct{}{}
	}
	return out
}

func toSeconds(amount float64, unit string) (int, bool) {
	unit = strings.TrimSuffix(strings.ToLower(unit), "s")
	switch {
	case strings.HasPrefix(unit, "second"):
		return int(amount), true
	case strings.HasPrefix(unit, "minute"):
		return int(amount * 60), true
	case strings.HasPrefix(unit, "hour"):
		return int(amount * 3600), true
	case strings.HasPrefix(unit, "day"):
		return int(amount * 86400), true
	default:
		return 0, false
	}
}

func submatches(text string, indexes []int) []string {
	out := make([]string, len(indexes)/2)
	for i := 0; i < len(indexes); i += 2 {
		if indexes[i] >= 0 {
			out[i/2] = text[indexes[i]:indexes[i+1]]
		}
	}
	return out
}

func lastNumeric(groups []string) string {
	for i := len(groups) - 1; i >= 1; i-- {
		if _, err := strconv.ParseFloat(groups[i], 64); err == nil {
			return groups[i]
		}
	}
	return ""
}

func lastNumberAndUnit(groups []string) (string, string) {
	for i := len(groups) - 1; i >= 1; i-- {
		if _, err := strconv.ParseFloat(groups[i], 64); err == nil && i+1 < len(groups) {
			for j := i + 1; j < len(groups); j++ {
				if regexp.MustCompile(`(?i)^(seconds?|minutes?|hours?|days?)$`).MatchString(groups[j]) {
					return groups[i], groups[j]
				}
			}
		}
	}
	return "", ""
}

func normalizeJSONNumber(v any) any {
	n, ok := v.(json.Number)
	if !ok {
		return v
	}
	if i, err := n.Int64(); err == nil {
		return int(i)
	}
	if f, err := n.Float64(); err == nil {
		return f
	}
	return v
}

func contains(values []string, wanted string) bool {
	for _, value := range values {
		if value == wanted {
			return true
		}
	}
	return false
}

func cloneMap(in map[string]any) map[string]any {
	out := make(map[string]any, len(in))
	for key, value := range in {
		out[key] = value
	}
	return out
}

func asMap(v any) (map[string]any, bool) {
	m, ok := v.(map[string]any)
	return m, ok
}

func stringValue(v any, fallback string) string {
	if s, ok := v.(string); ok && s != "" {
		return s
	}
	return fallback
}

func sha(content string) string {
	sum := sha256.Sum256([]byte(content))
	return hex.EncodeToString(sum[:])
}
