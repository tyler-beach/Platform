# Design: hardened analysis controls

## Goals

Make dual-write recovery, replay safety, and AI budget enforcement testable domain behavior. Keep the solution idiomatic Go, contract-first and operationally simple.

## Dispatch state and recovery

A job-creation transaction stores the canonical request fingerprint, idempotency identity, job row and durable dispatch intent together. A dispatcher claims intent with a lease/claim token, starts workflow execution, then records the result using compare-and-set/fencing. A periodic reconciler looks for expired leases and old pending intents.

A transactional outbox is one option; a DB-backed dispatch table can also work if transaction boundaries, lease ownership and recovery are explicit. The concrete choice remains open until the DB and workflow adapter are prototyped. The client receives acceptance after durable intent is committed, not when an in-memory process is scheduled.

## Idempotent effects and state ownership

Step Functions owns the top-level asynchronous state machine. The database is the durable business record. Every effect has a stable operation identity, typed outcome, attempt record and deadline. Stage handlers tolerate repeated delivery; logical findings and publications are protected by separate uniqueness/idempotency rules. Do not claim exactly-once execution.

Cancellation is best-effort, and completion may race with a cancellation request. Effectful stages must re-read/check state or a fencing version before persistence/publication. State transitions that lose the race are reconciled rather than silently overwritten.

## Token and spend reservation

The harness obtains an immutable assessment request and resolved budget policy, estimates/counts tokens, reserves maximum output plus cost headroom, and reserves call capacity before provider invocation. A durable job-level ledger is required because several Lambda invocations can run concurrently.

Each attempt records prompt/schema/model configuration, request ID, token-count method, estimate, reservation, returned usage, estimated/observed cost, error/retry category and final validation outcome. Failed calls are conservatively charged while usage is unknown. Retry, repair and verifier calls share the same job deadline and remaining allowance. Price values are effective-dated configuration; they do not belong in pure domain constants.

Deterministic compaction must preserve evidence IDs/source versions and required counter-evidence. If sufficient evidence cannot fit within policy, the result is inconclusive/review-required or stops before inference. Do not silently drop mandatory context to force the call.

## Functional and test design

Pure Go functions calculate canonical fingerprints, budget decisions, compaction order, state-transition eligibility and semantic evidence validation over explicit values. DB, clock/IDs, AWS, source, model, telemetry and publication effects remain in adapters/use cases.

Test-first plan:
- unit/table-driven tests for boundary arithmetic, state transitions and validators;
- property/fuzz tests for canonical order, fingerprint stability and parser/evidence bounds;
- integration tests for DB uniqueness, dispatch leases and provider usage reconciliation;
- fault injection at each dispatch/write/publish boundary;
- concurrent reservations and retry/cancellation races;
- labeled AI regression suite for evidence validity, abstention and relevant findings;
- redaction, cross-tenant and prompt-injection tests.

Use fake assessors for deterministic application tests. Labeled model evaluations are not a replacement for unit/contract tests and do not require identical prose across model runs.

## Operational posture

Start advisory/shadow only. Derive quality thresholds from a representative labeled pilot instead of inventing arbitrary percentages. Keep AI-only merge blocking disabled. Add dashboards/alerts for stuck dispatch intents, repeated retries, budget denials, spend drift, stale evidence, validation rejection, provider throttle and DB connection saturation.

## Decisions still open

- Transactional outbox versus DB-backed dispatch table/lease.
- Step Functions Standard versus Express.
- Concrete tenant identity/isolation and auth design.
- Initial budget limits, price source/versioning and conservative usage policy.
- How the provider data-processing policy governs source payloads.
- Database connection pooling and migration tooling.
