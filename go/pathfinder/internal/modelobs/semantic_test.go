package modelobs

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestValidateCandidatesBuildsRoleAndProvenanceFromPinnedArtifact(t *testing.T) {
	content := "Sessions expire after twenty minutes."
	artifacts := []SourceArtifact{{
		ID: "spec-1", Kind: "technical_specification", Role: RoleDesignAssertion,
		Path: "issue/tech-spec.md", Revision: "sha256:revision", Content: content,
	}}
	allowlist := []AllowedPredicate{{Predicate: "session.ttl_seconds", ValueType: "number", Subjects: []string{"session"}}}
	facts := []Candidate{{
		ArtifactID: "spec-1", Predicate: "session.ttl_seconds", Subject: "session", Value: float64(1200), Quote: content,
	}}

	got, rejected := ValidateCandidates(artifacts, facts, allowlist, 64)
	if rejected != 0 || len(got) != 1 {
		t.Fatalf("got %d evidence, rejected %d", len(got), rejected)
	}
	item := got[0]
	if item["evidence_role"] != RoleDesignAssertion || item["revision"] != "sha256:revision" || item["path"] != "issue/tech-spec.md" {
		t.Fatalf("trusted role/provenance not derived from artifact: %#v", item)
	}
	locator, ok := item["locator"].(map[string]any)
	if !ok || locator["start"] != 0 || locator["end"] != len(content) || locator["line"] != 1 {
		t.Fatalf("unexpected source locator: %#v", item["locator"])
	}
	if item["evidence_id"] == "" || item["source_sha256"] == "" {
		t.Fatalf("missing generated identity/provenance: %#v", item)
	}
}

func TestValidateCandidatesRejectsAmbiguousQuotesAndUnknownFacts(t *testing.T) {
	content := "TLS is required. TLS is required."
	artifacts := []SourceArtifact{{ID: "code-0", Kind: "implementation", Role: RoleImplementationFact, Path: "client.go", Revision: "git:abc", Content: content}}
	allowlist := []AllowedPredicate{{Predicate: "security.tls_policy.id", ValueType: "string", Subjects: []string{"service"}}}
	facts := []Candidate{
		{ArtifactID: "code-0", Predicate: "security.tls_policy.id", Subject: "service", Value: "tls-1-3-only", Quote: "TLS is required."},
		{ArtifactID: "missing", Predicate: "security.tls_policy.id", Subject: "service", Value: "tls-1-3-only", Quote: "TLS is required."},
		{ArtifactID: "code-0", Predicate: "unregistered.predicate", Subject: "service", Value: true, Quote: "TLS is required. TLS is required."},
		{ArtifactID: "code-0", Predicate: "security.tls_policy.id", Subject: "unapproved", Value: "tls-1-3-only", Quote: "TLS is required. TLS is required."},
		{ArtifactID: "code-0", Predicate: "security.tls_policy.id", Subject: "service", Value: true, Quote: "TLS is required. TLS is required."},
	}

	got, rejected := ValidateCandidates(artifacts, facts, allowlist, 64)
	if len(got) != 0 || rejected != len(facts) {
		t.Fatalf("invalid evidence accepted: evidence=%#v rejected=%d", got, rejected)
	}
}

func TestValidateCandidatesEvidenceIDIsStableForSourceVersion(t *testing.T) {
	content := "Session lifetime is twenty minutes."
	artifact := SourceArtifact{ID: "spec-1", Kind: "technical_specification", Role: RoleDesignAssertion, Path: "spec.md", Revision: "r1", Content: content}
	fact := Candidate{ArtifactID: "spec-1", Predicate: "session.ttl_seconds", Subject: "session", Value: 1200, Quote: content}
	allow := []AllowedPredicate{{Predicate: "session.ttl_seconds", ValueType: "number", Subjects: []string{"session"}}}
	first, _ := ValidateCandidates([]SourceArtifact{artifact}, []Candidate{fact}, allow, 64)
	second, _ := ValidateCandidates([]SourceArtifact{artifact}, []Candidate{fact}, allow, 64)
	if first[0]["evidence_id"] != second[0]["evidence_id"] {
		t.Fatalf("unstable IDs: %v / %v", first[0]["evidence_id"], second[0]["evidence_id"])
	}
	artifact.Revision = "r2"
	third, _ := ValidateCandidates([]SourceArtifact{artifact}, []Candidate{fact}, allow, 64)
	if first[0]["evidence_id"] == third[0]["evidence_id"] {
		t.Fatal("evidence ID did not change with source revision")
	}
}

func TestClientPreflightsAndMakesExactlyOneGenerationCall(t *testing.T) {
	content := "Session lifetime is twenty minutes."
	var countCalls, messageCalls int
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("x-api-key") != "test-secret" || r.Header.Get("anthropic-version") == "" {
			t.Errorf("required provider headers missing")
		}
		switch r.URL.Path {
		case "/v1/messages/count_tokens":
			countCalls++
			var request map[string]any
			if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
				t.Fatal(err)
			}
			if request["model"] != "model-test" || request["tools"] == nil || request["tool_choice"] == nil {
				t.Errorf("preflight did not count the structured request shape: %#v", request)
			}
			_, _ = fmt.Fprint(w, `{"input_tokens":123}`)
		case "/v1/messages":
			messageCalls++
			var request map[string]any
			if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
				t.Fatal(err)
			}
			if request["max_tokens"] != float64(4000) {
				t.Errorf("generation output was not capped: %#v", request["max_tokens"])
			}
			_, _ = fmt.Fprintf(w, `{"content":[{"type":"tool_use","name":"emit_normalized_evidence","input":{"facts":[{"artifact_id":"spec-1","predicate":"session.ttl_seconds","subject":"session","value":1200,"quote":%q,"evidence_role":"implementation_fact","path":"forged","revision":"forged","evidence_id":"forged"}]}}],"usage":{"input_tokens":123,"output_tokens":14}}`, content)
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	client := NewClient(Config{
		APIKey: "test-secret", Model: "model-test", BaseURL: server.URL,
		MaxInputTokens: 20000, MaxOutputTokens: 4000,
	}, server.Client())
	result, err := client.Normalize(context.Background(), []SourceArtifact{{
		ID: "spec-1", Kind: "technical_specification", Role: RoleDesignAssertion,
		Path: "issue/tech-spec.md", Revision: "sha256:rev", Content: content,
	}}, []AllowedPredicate{{Predicate: "session.ttl_seconds", ValueType: "number", Subjects: []string{"session"}}})
	if err != nil {
		t.Fatal(err)
	}
	if countCalls != 1 || messageCalls != 1 {
		t.Fatalf("calls: token_count=%d message=%d; want exactly one each", countCalls, messageCalls)
	}
	if len(result.Observations) != 1 || result.Metadata["input_tokens"] != 123 || result.Metadata["output_tokens"] != 14 {
		t.Fatalf("unexpected normalized result: %#v", result)
	}
	if result.Observations[0]["evidence_role"] != RoleDesignAssertion || result.Observations[0]["path"] != "issue/tech-spec.md" || result.Observations[0]["evidence_id"] == "forged" {
		t.Fatalf("model-controlled provenance was trusted: %#v", result.Observations[0])
	}
}

func TestClientStopsBeforeGenerationWhenTokenBudgetExceeded(t *testing.T) {
	var countCalls, messageCalls int
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/v1/messages/count_tokens" {
			countCalls++
			_, _ = fmt.Fprint(w, `{"input_tokens":20001}`)
			return
		}
		messageCalls++
		http.Error(w, "must not generate", http.StatusInternalServerError)
	}))
	defer server.Close()
	client := NewClient(Config{APIKey: "test-secret", Model: "model-test", BaseURL: server.URL}, server.Client())
	_, err := client.Normalize(context.Background(), []SourceArtifact{{
		ID: "spec-1", Kind: "technical_specification", Role: RoleDesignAssertion,
		Path: "spec.md", Revision: "sha256:rev", Content: "some spec",
	}}, []AllowedPredicate{{Predicate: "session.ttl_seconds", ValueType: "number", Subjects: []string{"session"}}})
	if !IsBudgetError(err) {
		t.Fatalf("err=%v, want budget error", err)
	}
	if countCalls != 1 || messageCalls != 0 {
		t.Fatalf("calls: token_count=%d message=%d; want 1 and 0", countCalls, messageCalls)
	}
}

func TestClientSkipsSecretLikeSourceBeforeAnyRequest(t *testing.T) {
	var requests int
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { requests++ }))
	defer server.Close()
	client := NewClient(Config{APIKey: "test-secret", Model: "model-test", BaseURL: server.URL}, server.Client())
	result, err := client.Normalize(context.Background(), []SourceArtifact{{
		ID: "code-0", Kind: "implementation", Role: RoleImplementationFact, Path: "config.go",
		Revision: "git:abc", Content: `api_key = "sk_live_0123456789abcdef"`,
	}}, []AllowedPredicate{{Predicate: "session.ttl_seconds", ValueType: "number", Subjects: []string{"session"}}})
	if err != nil {
		t.Fatal(err)
	}
	if requests != 0 || result.Metadata["status"] != "skipped_secret_detected" {
		t.Fatalf("secret-like input was sent: requests=%d metadata=%#v", requests, result.Metadata)
	}
}

func TestClientDoesNotRetryGenerationFailure(t *testing.T) {
	var countCalls, messageCalls int
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/v1/messages/count_tokens" {
			countCalls++
			_, _ = fmt.Fprint(w, `{"input_tokens":12}`)
			return
		}
		messageCalls++
		http.Error(w, "provider outage", http.StatusBadGateway)
	}))
	defer server.Close()
	client := NewClient(Config{APIKey: "test-secret", Model: "model-test", BaseURL: server.URL}, server.Client())
	_, err := client.Normalize(context.Background(), []SourceArtifact{{
		ID: "spec-1", Kind: "technical_specification", Role: RoleDesignAssertion,
		Path: "spec.md", Revision: "sha256:rev", Content: "session duration is 10 minutes",
	}}, []AllowedPredicate{{Predicate: "session.ttl_seconds", ValueType: "number", Subjects: []string{"session"}}})
	if err == nil || !strings.Contains(err.Error(), "upstream") {
		t.Fatalf("err=%v, want classified upstream failure", err)
	}
	if countCalls != 1 || messageCalls != 1 {
		t.Fatalf("calls: token_count=%d message=%d; want exactly one each", countCalls, messageCalls)
	}
}

func TestClientDeadlineStopsTokenPreflight(t *testing.T) {
	var generationCalls int
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/v1/messages/count_tokens" {
			select {
			case <-r.Context().Done():
				return
			case <-time.After(100 * time.Millisecond):
				_, _ = fmt.Fprint(w, `{"input_tokens":12}`)
			}
			return
		}
		generationCalls++
	}))
	defer server.Close()
	client := NewClient(Config{APIKey: "test-secret", Model: "model-test", BaseURL: server.URL, Timeout: 10 * time.Millisecond}, server.Client())
	_, err := client.Normalize(context.Background(), []SourceArtifact{{ID: "spec-1", Kind: "technical_specification", Role: RoleDesignAssertion, Path: "spec.md", Revision: "r1", Content: "session lifetime is ten minutes"}}, []AllowedPredicate{{Predicate: "session.ttl_seconds", ValueType: "number", Subjects: []string{"session"}}})
	if err == nil {
		t.Fatal("expected deadline error")
	}
	if generationCalls != 0 {
		t.Fatalf("generation calls=%d, want zero after preflight deadline", generationCalls)
	}
}
