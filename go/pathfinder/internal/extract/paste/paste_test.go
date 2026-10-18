package paste_test

import (
	"encoding/json"
	"os"
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/extract/paste"
)

var subjects = map[string]string{
	"api.auth_middleware.present":                      "public-api",
	"api.rate_limit.enabled":                           "public-api",
	"kubernetes.deployment.replicas":                   "workload",
	"kubernetes.pod_disruption_budget.max_unavailable": "workload",
	"kubernetes.pod_disruption_budget.present":         "workload",
	"kubernetes.readiness_probe.present":               "workload",
	"messaging.consumer.max_retries":                   "consumer",
	"privacy.sensitive_log.present":                    "logging",
	"security.encryption_at_rest.enabled":              "datastore",
	"security.secret_in_source.present":                "repository",
	"security.tls_policy.id":                           "edge",
	"session.ttl_seconds":                              "session",
}

func TestEnsureObservationsExtractsSamplePackage(t *testing.T) {
	raw, err := os.ReadFile("../../../../../.poc/requirement_catalog/sample_packages/multi-domain-session-service/package.json")
	if err != nil {
		t.Fatal(err)
	}
	var pkg map[string]any
	if err := json.Unmarshal(raw, &pkg); err != nil {
		t.Fatal(err)
	}
	pkg["observations"] = []any{}

	got, err := paste.EnsureObservations(pkg, subjects)
	if err != nil {
		t.Fatal(err)
	}
	byPredicate := observationValues(t, got["observations"])
	for predicate, want := range map[string]any{
		"session.ttl_seconds":                 720,
		"security.encryption_at_rest.enabled": true,
		"security.tls_policy.id":              "legacy-ssl",
		"kubernetes.deployment.replicas":      2,
		"kubernetes.readiness_probe.present":  true,
		"messaging.consumer.max_retries":      25,
		"privacy.sensitive_log.present":       true,
		"security.secret_in_source.present":   true,
	} {
		if got := byPredicate[predicate]; got != want {
			t.Errorf("%s=%v, want %v", predicate, got, want)
		}
	}
	extraction, ok := got["extraction"].(map[string]any)
	if !ok {
		t.Fatalf("extraction=%T, want object", got["extraction"])
	}
	if extraction["extractor"] != paste.ExtractorID || extraction["extractor_version"] != paste.ExtractorVersion {
		t.Fatalf("unexpected extraction metadata: %#v", extraction)
	}
}

func TestEnsureObservationsPreservesExistingWithoutSubjects(t *testing.T) {
	existing := []any{map[string]any{"predicate": "already.present"}}
	pkg := map[string]any{"observations": existing}
	got, err := paste.EnsureObservations(pkg, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(got["observations"].([]any)) != 1 {
		t.Fatalf("observations=%#v", got["observations"])
	}
	if _, added := got["extraction"]; added {
		t.Fatal("existing observations must not add extraction metadata")
	}
}

func TestExtractObservationsRequiresSubjects(t *testing.T) {
	_, err := paste.ExtractObservations(map[string]any{
		"tech_spec": map[string]any{"content": "Session TTL: 5 minutes."},
	}, nil)
	if err == nil {
		t.Fatal("expected missing subjects error")
	}
}

func TestConflictingValuesDropPredicate(t *testing.T) {
	observations, err := paste.ExtractObservations(map[string]any{
		"tech_spec": map[string]any{
			"path":    "tech.md",
			"content": "Sessions expire after 12 minutes.\nAlso session TTL of 5 minutes for mobile.",
		},
	}, subjects)
	if err != nil {
		t.Fatal(err)
	}
	if _, exists := observationValues(t, observations)["session.ttl_seconds"]; exists {
		t.Fatal("conflicting TTL observations must be dropped")
	}
}

func TestNoSecretMatchDoesNotInventFalse(t *testing.T) {
	observations, err := paste.ExtractObservations(map[string]any{
		"code": []any{map[string]any{
			"path":    "clean.go",
			"content": "package clean\nfunc Add(a, b int) int { return a + b }\n",
		}},
	}, subjects)
	if err != nil {
		t.Fatal(err)
	}
	if _, exists := observationValues(t, observations)["security.secret_in_source.present"]; exists {
		t.Fatal("silence must not emit security.secret_in_source.present=false")
	}
}

func TestGoPythonYAMLAndJSONPaths(t *testing.T) {
	tests := []struct {
		name      string
		path      string
		content   string
		predicate string
		want      any
	}{
		{
			name:      "go duration",
			path:      "session.go",
			content:   "package session\nconst SessionTTL = 12 * time.Minute\n",
			predicate: "session.ttl_seconds",
			want:      720,
		},
		{
			name:      "python lexical assignment",
			path:      "session.py",
			content:   "SESSION_TTL = 720\n\ndef auth_middleware(request):\n    return request\n",
			predicate: "api.auth_middleware.present",
			want:      true,
		},
		{
			name:      "kubernetes yaml",
			path:      "deploy.yaml",
			content:   "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: app\nspec:\n  replicas: 3\n  template:\n    spec:\n      readinessProbe:\n",
			predicate: "kubernetes.deployment.replicas",
			want:      3,
		},
		{
			name:      "json config",
			path:      "config.json",
			content:   `{"session":{"ttl_seconds":600},"encryptionAtRest":true}`,
			predicate: "session.ttl_seconds",
			want:      600,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			observations, err := paste.ExtractObservations(map[string]any{
				"code": []any{map[string]any{"path": tt.path, "content": tt.content}},
			}, subjects)
			if err != nil {
				t.Fatal(err)
			}
			if got := observationValues(t, observations)[tt.predicate]; got != tt.want {
				t.Fatalf("%s=%v, want %v", tt.predicate, got, tt.want)
			}
		})
	}
}

func observationValues(t *testing.T, raw any) map[string]any {
	t.Helper()
	items, ok := raw.([]any)
	if !ok {
		t.Fatalf("observations=%T, want []any", raw)
	}
	out := make(map[string]any, len(items))
	for _, rawItem := range items {
		item, ok := rawItem.(map[string]any)
		if !ok {
			t.Fatalf("observation=%T, want object", rawItem)
		}
		out[item["predicate"].(string)] = item["value"]
	}
	return out
}
