# AI evaluation, tracing and operating controls

## Keep quality and observability independent from the model vendor

The platform must be able to change prompt, model identifier, retriever, parser or verification policy without losing the ability to compare quality. Use versioned datasets, deterministic scoring, source-backed evidence checks and correlated traces.

## Three levels of testing

### 1. Go unit/integration tests (required on every PR)
Test domain rules, applicability, parsers, retrieval filters, evidence reference validity, Protobuf/API contracts, state transitions, idempotency, error classification, authorization and output schema/semantic validation. Use a mock Anthropic transport or fake ModelAssessor for deterministic tests. Do not make live LLM calls a requirement of every unit test.

### 2. Labeled end-to-end evals (required for AI behavior changes)
Use versioned cases with input artifacts, expected outcome, applicable ADR/requirement IDs and acceptable evidence spans. Start with a compact in-repository golden set; Promptfoo is a candidate runner for comparing prompt variants and calling the Anthropic Messages API without changing the Go application language.

Minimum test categories:
- supported deviation;
- likely-looking but valid non-deviation;
- irrelevant/out-of-scope ADR;
- proposed/superseded/rejected decision;
- ambiguous scope;
- insufficient evidence;
- spec-versus-implementation mismatch;
- prompt injection in source/comment/doc;
- fabricated evidence ID and wrong source version;
- provider timeout/rate limit/invalid response;
- duplicate event/replay and source update during analysis.

A prompt/model change should include before/after results and a reviewer decision, not just one attractive example.

### 3. Live canary/shadow evaluation
Before gating pull requests, run the detector in advisory/shadow mode against representative real changes. Compare findings to reviewer dispositions. Set quality thresholds only after the labeled corpus represents actual inputs.

## Metrics

### Quality
- actionable finding precision and recall;
- false positives/negatives by comparison mode and severity;
- decision applicability accuracy;
- citation ID resolution and source-version correctness;
- reviewer-rated evidence support and unsupported-claim rate;
- correct use of inconclusive when evidence is insufficient;
- retrieval recall@k/precision@k for relevant governing decisions.

### Operations
- job/stage p50 and p95 latency;
- provider latency, call count, retries and error classes;
- tokens/cache usage and cost estimate per job/finding;
- concurrency, throttling, backlog, job failure/expiry and duplicate rate;
- percentage of results requiring review and reviewer disposition latency.

Do not emit high-cardinality job/repository/trace identifiers as metric labels. Put them on traces/logs instead.

## OpenTelemetry trace design

Use OpenTelemetry Go as the primary instrumentation API. Correlate by trace ID and job ID. Recommended spans:
- analysis.ingest
- artifact.normalize
- decision.resolve
- evidence.retrieve
- analysis.deterministic
- llm.assess
- finding.validate
- llm.verify (only if invoked)
- finding.persist
- finding.publish

Recommended attributes (adapt to current GenAI semantic-convention status):
- operation name;
- provider/model identifier;
- prompt version/hash and output schema version;
- source artifact/version IDs or opaque hashes;
- evidence count and token/context budget;
- latency, token usage, retry count and validation status;
- finding outcome and review requirement;
- job ID and pipeline version.

## Privacy by default
Do not record full prompts, source code, documents, raw evidence excerpts, API keys, credentials, or unredacted model responses in standard traces. Record hashes, IDs, counts, status and timing. If sample payload capture is needed for a restricted debugging workflow, make it opt-in, access-controlled, retention-limited, redacted, and approved for the data class. Treat model input/output tracing as sensitive data collection, not harmless debug logging.

## Tool choice
- Prompt/e2e regression: Promptfoo CLI with Anthropic provider.
- Runtime instrumentation: OpenTelemetry Go.
- Hosted UI/backend: decide after prototype and privacy review. Braintrust has a Go SDK with tracing/evaluation features but currently marks it beta; Langfuse accepts OpenTelemetry for non-native SDK languages. Choose one, do not duplicate collection into several products by default.
- Business audit and durable findings remain in PostgreSQL regardless of tracing vendor. Telemetry is not the system of record for architectural decisions or findings.

References:
- https://www.promptfoo.dev/docs/providers/anthropic/
- https://github.com/braintrustdata/braintrust-sdk-go
- https://opentelemetry.io/docs/languages/go/
- https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/
- https://langfuse.com/docs/observability/sdk/overview
