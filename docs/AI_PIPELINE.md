# AI pipeline and harness

## Principle
The model is one bounded stage in an auditable process, not the whole platform. Build the evidence package first, use the model for a defined judgment, then validate the result in application code.

## Pipeline
1. Accept request/event and create an idempotent job.
2. Resolve immutable input versions (base/head commit, spec version, ADR versions).
3. Normalize artifacts and extract deterministic metadata.
4. Resolve applicable decision/requirement candidates using status, scope, owner, relationships, identifiers and search.
5. Run deterministic analysis: diffs, AST/symbol inspection, document parsing and explicit rules.
6. Assemble a budgeted evidence package with stable evidence IDs.
7. Call Anthropic for structured assessment.
8. Validate schema, evidence references, source versions and domain invariants.
9. For selected findings, run an independent challenge/verification pass with bounded input and output.
10. Persist finding, verification, source/version provenance, prompt/schema/model metadata and cost/latency telemetry.
11. Publish advisory results or route for human review.

## Model operations
Start with a minimal number of prompts/calls; split operations only when separate context, permissions, output contracts or evaluation show it helps.
- **Requirement extraction:** atomic, traceable requirements from plain English; preserve modality (MUST/SHOULD/MAY) and ambiguity.
- **ADR interpretation:** decision statement, status, rationale, consequences, scope, constraints, exceptions, effective date, supersession links.
- **Applicability assessment:** identify whether the decision applies to a service/repo/change/version; allow unknown.
- **Deviation assessment:** compare relevant source facts and decisions, returning supported deviation, no deviation found, or inconclusive.
- **Verification:** deterministic validation first; optional independent model challenge for selected results.
- **Explanation:** summarize verified claims and link to evidence, not unrestricted context.

## Go harness interface (illustrative)
~~~go
type ModelAssessor interface {
    Assess(ctx context.Context, req AssessmentRequest) (AssessmentResult, error)
}
~~~
Define concrete request/result structs; keep provider-specific message types out of domain packages. Adapter responsibilities: request construction, deadlines, provider errors, bounded retry, token/cost attribution, response parsing and version metadata. Configure model name; don't scatter model identifiers throughout the code.

## Structured output is not truth
Prefer schema-constrained output where supported, then validate again in Go:
- required fields and enum membership;
- max lengths and collection sizes;
- evidence IDs are in the job's provided evidence package;
- source version matches the job;
- applicable decision status/scope is valid or applicability is explicitly unknown;
- finding doesn't contradict itself or duplicate an existing result;
- rationale includes support from supplied evidence.
If output is invalid, allow at most one controlled repair attempt where safe, then return an invalid/inconclusive result. Never loop indefinitely.

## Evidence package
Each item should contain stable evidence ID, artifact/version or hash, source type, location (path/line, symbol, section or immutable URL), excerpt, retrieval method, source integrity metadata and relevance rationale. Store authoritative source separately; send only necessary excerpts. Preserve line/symbol/section mappings across normalization.

## Retrieval order
1. Exact artifact/ADR/requirement IDs and explicit relationships.
2. Metadata filters (status, service, repository, environment, owner, dates).
3. Changed file paths, symbols, imports, API names, infrastructure resource types and config keys.
4. Full-text search.
5. Embedding search for semantic candidates missed by exact/lexical retrieval.
6. Optional reranking only after retrieval evaluation.
Vector similarity must not determine normative applicability. Source docs and metadata remain authoritative.

## Budgeting, caching, versioning
Set limits for evidence count, excerpt size, input/output tokens, calls, wall-clock time and cost per job. Record prompt/schema version/hash, operation, requested/returned model IDs when available, relevant request settings, source evidence IDs, provider response ID, token usage, latency, attempts, validation status and estimated cost. Cache only when keys include immutable source versions, operation, prompt/schema version and model settings.

## Error classification
- network/timeout/5xx: bounded retry with jitter;
- throttling: respect retry guidance and cap concurrency;
- auth/permission error: fail fast and alert;
- invalid request/unsupported input: fail fast;
- invalid response: one bounded recovery attempt, then typed failure/inconclusive;
- missing/stale evidence: inconclusive/review required, not guessed.

## Avoid at first
No free-form repository-agent loop, multi-agent debate on every finding, dedicated memory product for architectural knowledge, vector DB as sole source, or model-controlled ADR/code/infrastructure changes. Start with a small, versioned, observable harness rather than an AI framework for its own sake.
