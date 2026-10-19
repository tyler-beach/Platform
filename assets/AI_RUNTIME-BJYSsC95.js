const e=`# AI runtime contract: token budgets, provenance and safe execution

**Status:** Proposed contract for implementation. It is not proof that a model harness or budget ledger exists.

## Purpose

Every model invocation must be a named, versioned, bounded, authorized effect. Context-window limits alone do not cap spend, retries or concurrent calls. This contract covers preflight admission, runtime accounting, provenance, failure behavior and privacy.

## Budget policy

Resolve a versioned policy before building a request. Exact defaults remain a product/operations decision and must not be guessed in code.

| Limit | Scope | Required behavior |
|---|---|---|
| Input tokens | Operation and job | Count exact supported request shape or use a conservative versioned estimate; compact deterministically or stop |
| Output tokens | Individual call | Always set a maximum; reserve the maximum output budget before admission |
| Cumulative token usage | Job | Count each attempt; reconcile estimate with returned usage |
| Cost | Job, workspace/tenant and global | Enforce ceiling/reservations before calls; provider-reported usage and effective-dated prices reconcile estimates |
| Call count / retries | Job and operation | Assessment, repair, retries and optional verification share a finite allowance |
| Wall-clock time | Job and call | Propagate deadline and cancellation; never restart deadline on retry |
| Concurrency / rate | Workspace and global | Admit or queue work before provider throttling becomes a retry storm |
| Evidence size | Package and operation | Bound evidence items/excerpt size; preserve required/counter-evidence and record truncation |

Budget exhaustion is a domain/operational state with stable reason metadata. It is not silently retried with a reset allowance. A call denied before sending does not count as provider usage but does create an audit/telemetry event. Once a request might have reached the provider, charge conservatively until actual usage reconciles it.

## Preflight and accounting sequence

1. Resolve configured model ID/alias, operation, prompt hash/version, schema hash/version, pipeline/policy version, request options and price catalog version.
2. Build the request to be sent, including system prompt, user content, output schema/tool definitions, cache directives and supported text/image/document blocks.
3. Count input tokens using the provider's token-count endpoint for supported request shapes. Record API version and method; fall back to a conservative model-aware estimate only when necessary.
4. Calculate input tokens + maximum output tokens + defined overhead/headroom; reject or compact if the operation/context ceiling would be exceeded.
5. Atomically reserve the maximum expected spend/call slot against cumulative job budget so parallel branches cannot independently overspend. Reservation needs idempotency and a lease/expiry/reconciliation policy for worker crashes.
6. Invoke with timeout, cancellation, maximum output tokens and classified retry policy.
7. Reconcile provider usage (input, output, cache read/write or other returned categories), provider request ID and model ID. Calculate observed cost using the effective price version; retain the original estimate.
8. Release unused reservation and commit actual spend. If usage is unknown after timeout, keep a conservative pending/estimated charge until reconciliation or operator resolution.
9. Before retry, repair or verification, check the remaining job budget again. A retry is another attempt, not a new job budget.

The ledger must account for parallel invocations and retry crashes. Define the durable atomicity strategy before code; simple in-memory counters are not acceptable across Lambda invocations.

## Deterministic compaction rules

- Order candidates by explicit source/decision authority, applicability, deterministic relevance and stable tie-breaker.
- Keep source/version/locator metadata and stable evidence IDs.
- Keep counter-evidence and decision status/scope; never optimize tokens by dropping a required governing decision silently.
- Record removed evidence IDs and reason codes with the assessment provenance.
- If the remaining package cannot satisfy required evidence within budget, return insufficient evidence/inconclusive or route to review; don't force a model answer.
- Hash the canonical request payload/metadata without placing raw source text in ordinary logs.

## ModelRun metadata

At minimum, record:
- model provider, configured alias and resolved model ID where available;
- operation, prompt ID/version/hash, schema version/hash, pipeline/policy version;
- immutable input/source version refs and exact evidence IDs sent;
- request options, maximum output tokens, counting method/version and token estimate;
- budget policy/reservation ID, price catalog version and cumulative budget decision;
- provider request/response ID where available, attempt/retry index and classified error;
- returned usage categories, estimated and observed cost status, latency;
- response-schema and semantic-validation result/version;
- cache usage when the provider reports it, review/stop decision and correlation IDs.

Do not store hidden model reasoning. Raw prompt/response retention is a separate restricted data policy, not default ModelRun metadata.

## Cache semantics

Provider prompt caching is an optimization for supported stable prefixes. It is neither a truth mechanism nor a substitute for budget accounting. If assessment results are cached, keys must include immutable source/evidence version, comparison mode, applicable decision versions, policy/pipeline, prompt/schema, model settings and relevant authorization scope. Recheck permission and publication freshness on cache hit. Do not use cross-tenant cache keys that reveal content or bypass access rules.

## Security and telemetry

- Never include credentials/secrets as model context or model tools.
- Model output cannot authorize access, alter workflow routing, call arbitrary tools, publish a result or reset a budget.
- Standard traces/logs contain operation, versions/hashes, IDs where appropriate, usage, cost estimate, duration, retry/error category and validation status—not full prompts, source excerpts or responses.
- Redact provider error bodies and headers before logging.
- Any content capture for debugging/evaluation is opt-in, access-controlled, audited, redacted and retention-limited.
- Avoid high-cardinality identifiers as metric labels.

## Minimum tests

- Input + reserved output exactly at and one token beyond policy boundaries.
- Schema/tool prefix changes affect token estimate and prompt version.
- Concurrent reservations cannot exceed the job budget.
- Retry/repair/verification consume one cumulative allowance.
- Timeout after request submission preserves conservative charge until reconciled.
- Price configuration missing/stale fails safe; estimated vs actual cost are distinguishable.
- Deterministic compaction yields same evidence order and records every omission.
- Budget exhausted prevents further provider calls, even on API retry/replay.
- Redacted logs omit seeded secrets, source snippets and raw prompts.
- Cache hit never bypasses authorization, source freshness or budget policy.
`;export{e as default};
