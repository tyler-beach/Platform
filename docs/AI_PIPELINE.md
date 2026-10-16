# AI pipeline and harness

## Principle

The model is one bounded, auditable stage, not the system orchestrator or source of truth. Build deterministic evidence first, use a named model operation for a specific judgment, and validate the output in application code.

## Pipeline

1. Authenticate, authorize, validate and canonicalize the request.
2. Commit a job, idempotency record and durable workflow-dispatch intent.
3. Resolve immutable source versions and pin parser/pipeline/policy versions.
4. Normalize artifacts and extract deterministic metadata.
5. Resolve candidates through status, scope, relationships, identifiers, changed symbols and lexical retrieval.
6. Run applicable deterministic diff/AST/document/config rules and record branch completeness.
7. Assemble an immutable, stable-ordered evidence package with IDs tied to source versions.
8. Preflight token, call, concurrency, cost and deadline budgets.
9. Call Anthropic for one bounded structured assessment.
10. Validate schema, evidence references, source versions, applicability, counter-evidence and domain invariants.
11. Run optional independent verification only for policy-selected cases and within remaining budget.
12. Persist finding, evidence, model-run, usage and audit data; publish idempotently only after freshness and review policy.

## Operations

Start with few named operations, splitting only when evaluation proves value or distinct permissions, context, output contract or budget require it:
- **Requirement extraction:** atomic traceable requirements from plain English; preserve MUST/SHOULD/MAY and ambiguity.
- **ADR interpretation:** decision, status, scope, constraints, consequences, exceptions, effective date and supersession.
- **Applicability:** whether the decision governs this component/revision; unknown is a valid result.
- **Deviation assessment:** compare source-backed facts and requirements; return a domain outcome, not unsupported prose.
- **Verification:** deterministic checks first; selective independent challenge only where justified.
- **Explanation:** summarize validated claims and cite evidence; don't let unrestricted model knowledge add new factual assertions.

## Typed Go boundary

~~~go
type ModelAssessor interface {
    Assess(ctx context.Context, req AssessmentRequest) (AssessmentResult, error)
}
~~~

This is illustrative. Keep provider-specific SDK request/response types in the adapter. The harness owns operation allowlists, prompt/schema selection, token/cost budgets, deadlines, cancellation, response parsing, provider error classification, usage metadata and validation integration.

## Token and cost management

Token controls are enforced **before and during** each call. A per-call context-window limit alone does not cap cumulative spend.

1. Resolve configured model, request options, prompt/schema version and effective-dated price configuration.
2. Build the exact candidate request, including system prompt, evidence, output schema/tool definitions and supported content blocks.
3. Count request tokens using the Anthropic token-count endpoint where supported for that request shape; otherwise use a conservative model-aware estimator and retain the estimation method/version.
4. Reserve the configured maximum output tokens and conservative overhead before admitting the call.
5. Enforce per-operation input/output caps, cumulative per-job token/spend/call/retry caps, one end-to-end deadline, and per-tenant/global concurrency ceilings.
6. Compact by deterministic relevance and record which evidence IDs were removed and why. If the package still does not fit, reject/route/review rather than silently dropping required evidence.
7. Account for failed/retried calls as potentially billable unless provider usage proves otherwise. Retry, repair and optional verification consume the same job budget.
8. Reconcile estimates to provider-reported usage after each call. Persist actual/estimated status, request ID, price version, latency and attempts.
9. Stop or skip optional verifier calls when there is not enough remaining reserve.

Use price/model settings as versioned configuration, not constants embedded in domain code. Prompt caching is optional and measured; it is not a result cache. Any result-cache key includes immutable input/evidence versions, operation, prompt/schema/pipeline/policy versions and model configuration; authorization and freshness are still rechecked.

See the [token budget diagram](assets/diagrams/token-budget.svg) and [adversarial review](ADVERSARIAL_DESIGN_REVIEW.md). Anthropic's [token-counting documentation](https://platform.claude.com/docs/en/build-with-claude/token-counting) describes preflight estimation and request-shape support; the harness still needs a cumulative spend ledger.

## Structured output is not truth

Use constrained structured output where supported, then validate in Go:
- required fields/enums, length and collection bounds;
- every evidence ID belongs to this exact job package;
- artifact version and source locator match the immutable snapshot;
- decision status/scope and applicability are valid or explicitly uncertain;
- supporting and contradicting evidence are both considered;
- no contradiction, duplicate finding or unsupported factual assertion;
- outcome, severity, evidence quality/confidence and review requirement stay distinct.

Schema-valid but unsupported output is rejected or downgraded according to explicit policy. Permit at most one controlled repair attempt only where safe and budgeted; otherwise produce a typed failure/inconclusive result. Never turn timeout, refusal, invalid output or missing evidence into “no deviation found.”

## Evidence package and retrieval

Each evidence item carries stable ID, artifact/version/hash, source type, precise path/line/symbol/section, locator precision, excerpt digest, retrieval method/version, integrity, collection timestamp and relevance rationale. Keep source truth outside model context; send only minimum necessary excerpts.

Retrieval precedence:
1. Exact IDs and authoritative relationships.
2. Status/scope/owner/service/environment/time filters.
3. Changed paths, symbols, imports, API names and config/resource identifiers.
4. Full-text search.
5. Embedding search for evaluated semantic recall gaps.
6. Reranking only where a labeled benchmark proves benefit.

Vector similarity must never decide normative applicability. Required branch failures and missing source mappings remain explicit.

## Failure classification

- Network/timeout/5xx: bounded retry with jitter if the operation is safe.
- Rate limit: honor provider retry guidance; keep the original deadline and budget.
- Auth/permission: fail fast, alert without logging secret payloads.
- Invalid request/unsupported content: fail fast or route to a supported parser.
- Invalid model response: bounded repair at most once, then typed failure/inconclusive.
- Stale or insufficient evidence: report incompleteness; do not guess.
- Budget exhausted: stop or route for review; never reset the cap on retry.

## Avoid initially

No free-form repository-agent loop, multi-agent debate on every finding, conversational memory product for ADR facts, vector DB as the sole source, or model-controlled source/infra writes. Start with a small, versioned and observable harness.
