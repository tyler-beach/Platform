const e=`# Adversarial design review

**Review date:** 2026-10-16  
**Scope:** Proposed architecture, API/data/evidence contracts, Go programming model, distributed execution, LLM operations, and OpenSpec practice.  
**Status:** Design review only. The production API, persistence layer, workers, workflow, and model harness are not implemented. These are design findings, not verified production vulnerabilities or completed remediations.

## Executive verdict

The direction is sound: evidence first, typed Go boundaries, Step Functions for asynchronous lifecycle, versioned artifacts, direct Anthropic API behind a narrow harness, and application-side validation. The biggest risk is turning sound principles into prose without enforceable state, budget, identity and test contracts.

The companion OpenSpec change, [hardened-analysis-controls](https://github.com/tyler-beach/Platform/blob/main/openspec/changes/hardened-analysis-controls/proposal.md), is a **proposed contract delta**, not implemented behavior. Its tasks must remain open until code and tests demonstrate the guarantees.

## Priority findings

| Priority | Finding | Failure mode | Required control / proof |
|---|---|---|---|
| P0 | Database + workflow dual write | Job committed, workflow start fails, caller sees an accepted job that never runs; lost responses may launch duplicate work | Durable dispatch intent/outbox or equivalent reconciler; deterministic execution identity; idempotent start; test failure after DB commit and around workflow start |
| P0 | No enforceable cumulative model budget | Retries, repair and verification multiply spend or exhaust quota | Hard per-job spend/call/token/deadline ceiling plus per-tenant/global concurrency; charge failed attempts conservatively; persist usage reconciliation |
| P0 | Identity confused with selectors | User-supplied workspace, repository, URL, artifact ID or page token becomes authority | Authenticate first; authorize every read, dereference, cancel and publish; scope DB/object queries by tenant; test cross-tenant refs |
| P1 | At-least-once mistaken for exactly-once | Duplicate findings, audits, model spend, workflow starts or external comments | Canonical request hash, unique constraints, per-effect operation identity, dispatch reconciliation and publication idempotency |
| P1 | State authority split across DB, Step Functions and an AI graph | Conflicting status, cancellation and retry semantics | Step Functions owns async lifecycle; DB is durable business state; any future AI graph is a bounded sub-workflow only |
| P1 | Branch failures hidden | Timeout silently narrows evidence and creates false assurance | Explicit required/optional branches, completeness markers and partial-result policy |
| P1 | Workflow state grows with source text | Payload-limit errors, duplicated data and sensitive content exposure | Keep state to IDs, hashes, status and small summaries; large content remains in bounded external storage |
| P1 | Cancellation races with effects | A worker commits or publishes after cancellation was acknowledged | Best-effort cancellation semantics, fencing/state checks before commit and publication, and audit of accepted vs completed cancellation |
| P1 | Schema-valid output treated as correct | Fabricated IDs, wrong-version locators, invalid applicability or unsupported claims | Validate evidence membership/version/locator, status/scope, counter-evidence and state transitions in Go |
| P1 | Source/secret data leaks into telemetry | Proprietary excerpts or credentials enter trace/log backends | Metadata-first telemetry, redaction tests, separate access-controlled payload capture with explicit retention/audit |
| P1 | LLM tests are anecdotal | Prompt/model drift degrades precision or abstention unnoticed | Versioned labeled corpus, before/after comparison and reviewed thresholds based on a representative pilot |
| P2 | Functional core stays advisory | Hidden I/O, mutable collections and non-canonical order harm determinism | Pure domain packages, explicit adapters, ownership rules, stable sort, property/fuzz tests |
| P2 | Retention and deletion are underspecified | Snapshots, derived indexes, logs, transcripts and audit have conflicting lifecycles | Define retention/deletion per data class and link derived indexes to source versions |
| P2 | API/deployment profile not settled | Premature gRPC operations or an HTTP design that misses actual consumer needs | Pick simplest real consumer; settle HTTP/Lambda vs long-lived gRPC before provisioning |

## Distributed systems: required invariants

### Acceptance and dispatch

Do not rely on “write job, then call StartExecution, then return 202” as an atomic operation. A database and Step Functions do not share a transaction. The target design must commit job + idempotency record + durable dispatch intent in one database transaction. A dispatcher/reconciler claims intent with a lease, starts the workflow with deterministic execution identity where supported, then records the result. If the process dies at any boundary, another attempt must reconcile safely. A transactional outbox is one option; a DB-backed dispatch table and lease may suffice. Select and test one implementation before production.

Return acceptance only after durable intent is committed, not merely after an in-memory goroutine is started. The API, dispatcher and worker must not each invent their own job state.

### Idempotency and replay

Exactly-once distributed execution is not a realistic promise. Require **at-least-once delivery with idempotent logical effects**:
- Request identity = authorized workspace + caller idempotency key + canonical request hash.
- Same key and same request returns the same logical job; same key and different request returns a conflict.
- Stage identity includes job, immutable inputs, stage/pipeline/policy version and operation identity.
- Finding uniqueness uses a versioned canonical fingerprint; publication has a separate idempotency identity.
- Every attempt is observable, but attempts must not mutate historical source snapshots or duplicate the logical finding.
- Retry rules respect the original deadline and cumulative spend/call allowance.

### Lifecycle and concurrency

Model explicit transitions and terminal semantics for queued, running, needs-review, succeeded, failed, cancelled and expired. Separate domain outcomes from execution states and errors. Define the boundary between technical failure and review-required state. Use optimistic versioning or another compare-and-set/fencing mechanism when cancellation, retry, reprocessing or publication may race. A cancellation acknowledgement means the request was recorded, not that a completed external effect was rolled back.

For fan-out/fan-in, each branch reports status, completeness and source/policy version. Required branch failure leads to bounded retry or an incomplete/inconclusive outcome. Optional branch failures remain visible as limitations. Bound parallelism by tenant, job and global limits.

### Data and cloud boundaries

- Keep Step Functions state small: job/stage IDs, hashes, versioned refs and bounded summaries. Store large source/evidence content separately under explicit size and retention policy.
- Make snapshots immutable and addressable by source identity, version and hash. Treat S3 version/checksum and DB metadata consistency as a designed workflow, including orphan cleanup.
- Database constraints—not only application checks—should enforce key uniqueness and references where practical. Use expand/contract schema migrations and test old/new reader compatibility.
- Size database connections for peak Lambda concurrency. Evaluate RDS Proxy only if connection pressure warrants it.
- Do not add SQS/EventBridge, another database, vector service, gRPC or agent graph without a consumer/operational justification.

## Token, context and spend policy

Token handling is an admission and runtime control, not merely prompt trimming. Each model operation needs:
- named operation plus prompt/schema versions;
- maximum input and output tokens;
- deterministic compaction policy with removed evidence IDs and reasons recorded;
- per-call deadline/output cap;
- cumulative per-job token, call-count, retry-count and spend ceilings;
- overall job deadline;
- per-tenant and global concurrency/rate limits;
- price/model configuration version;
- usage metadata and request IDs per attempt, including retried attempts where usage is available.

Preflight must count or conservatively estimate the actual request shape, including system prompt, structured schema/tool definitions and supported content blocks. Reserve configured maximum output tokens before admitting the call. If input + reserved output + overhead does not fit, deterministically compact, route to a suitable operation/model or stop. The Anthropic token-counting endpoint is useful where supported by the selected request form; it does not replace the job spend ledger.

Use a durable reservation/ledger or serialized budget claim so parallel workers cannot each spend the full same job budget. Reconcile estimates against provider usage after each call. Retry, repair and optional verification consume the same cap. Skip or stop optional verification if reserve is insufficient. Do not hard-code price assumptions into domain logic; use effective-dated configuration and distinguish estimated from observed cost. Prompt caching is an optimization, not a correctness guarantee or substitute for validation. Cache does not bypass authorization, provenance, freshness checks or spend accounting.

See [token controls diagram](assets/diagrams/token-budget.svg), [AI pipeline](AI_PIPELINE.md), and [logging/audit contract](contracts/LOGGING_AND_AUDIT.md).

## Functional engineering review

Keep a practical functional core / imperative shell:
- Pure functions: state-transition decisions, applicability from explicit snapshots, deterministic rule evaluation, evidence ranking/compaction, budget arithmetic, candidate validation and fingerprints.
- Effects: DB reads/writes, cloud/source APIs, clock/IDs, model calls, workflow starts, telemetry and publication.
- Ownership: after a stage publishes a value, it does not mutate shared maps/slices/pointers. Copy at ownership boundaries; avoid needless deep copies of large blobs.
- Canonicalization: sort evidence/output before prompts, fingerprints and deterministic tests.
- Error model: idiomatic Go errors with typed categories. Inconclusive is a domain outcome; provider timeout is an execution failure, never a “no deviation” finding.
- Policy: authorization, applicability and state transitions are enforced in code, not solely in prompts or Step Functions expressions.
- No custom monad/effect framework, global mutable job state or interface for every helper.

Test pure core without live AWS/DB/Anthropic; test adapters through fakes/containers and integration tests; use labeled AI evaluations for model-dependent quality. Functional programming does not eliminate transactions, uniqueness constraints, race conditions or idempotency.

## Contract and test coverage matrix

| Contract surface | Minimum proof |
|---|---|
| Protobuf/OpenAPI | Lint, build, breaking-change and mapping/compatibility checks |
| Evidence | Wrong job/tenant/version, unknown IDs, stale source, bad line ranges, hash mismatch, counter-evidence and stable fingerprint |
| Lifecycle | Table-driven transition tests, terminal states, cancellation races and replay |
| Dispatch | Inject crashes before/after DB commit, before/after workflow start and after a lost response |
| Token budget | Exact-cap boundary, reserved-output overflow, concurrent reservations, retry charging, missing prices, timeout after provider acceptance, verifier denied |
| Security | Cross-tenant selectors, prompt injection, malicious Markdown, secret redaction, parser abuse and denial-of-wallet |
| AI quality | Deviation, valid non-deviation, irrelevant/superseded ADR, ambiguity, insufficient evidence, fabricated citation and model drift |
| Operations | Backlog/throttling/provider outage, DB pool saturation, partial branch failure, replay, stale publication and audit retrieval |

## Open decisions — do not guess

Before production, explicitly decide and record owner/rationale/date for: API profile and auth scheme; Standard vs Express Step Functions; dispatch/outbox mechanism; initial input formats; tenant isolation model; retention/deletion classes; provider data-processing approval; idempotency retention; token/spend defaults; token-counting fallback; evaluation thresholds; DB pooling/migration tools; publication and human-override policy.

## Completion gate

Architecture and docs describe target controls and an active OpenSpec delta proposes enforceable requirements. Controls are **not complete until implemented, fault-tested, reviewed, and the change is archived only after acceptance scenarios pass**.
`;export{e as default};
