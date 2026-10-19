const e=`# Workflow operations and reliability

## Ownership boundaries

- **Ingress/API:** authentication and authorization, request validation, idempotent acceptance, query/cancel operations.
- **Dispatch controller/reconciler:** drains durable workflow-start intent and repairs ambiguous starts.
- **Step Functions:** the one owner of asynchronous stage sequencing, branching, retry/catch policy, timeouts and execution lifecycle.
- **Go Lambda workers:** bounded normalization, retrieval, deterministic analysis, assessment, validation, persistence and publication effects.
- **PostgreSQL:** authoritative jobs, idempotency, findings, model usage/provenance, reviews and audit records.
- **OpenTelemetry:** operational correlation only, not business audit.

Do not execute the full analysis inline in the API. Do not run competing job state machines in the API, a model framework and Step Functions. Do not host a gRPC listener in Lambda workers.

## Acceptance and workflow-start recovery

Database commit and Step Functions start are a distributed dual write; they cannot be made atomic by arranging two calls in sequence. The intended production design must:
1. Commit the job, canonical request fingerprint, idempotency row and dispatch intent in one database transaction.
2. Return acceptance only after that durable commit.
3. Let a dispatcher claim intent using a lease/claim token and start the workflow with a deterministic execution identity where supported.
4. Record dispatch result with compare-and-set/fencing so stale dispatchers cannot overwrite newer state.
5. Retry/reconcile ambiguous starts safely; duplicates converge on the same logical job.
6. Alert on old pending dispatch intent and provide an operator reconciliation/runbook path.

A transactional outbox is one implementation option; a DB-backed dispatch table plus leases may suffice. Select one and add failure-injection tests before production.

## Job and stage semantics

Model explicit states and allowed transitions. Separate domain outcomes from execution states/errors. Define NEEDS_REVIEW semantics explicitly; do not hide a technical failure in a review state.

Every external operation has a deadline, classified error, bounded retry policy, attempt identity and observable result. A retry shares the original overall deadline and model budget. Cancellation is best-effort: record the request, stop future work where possible, and fence late commits/publication; never promise rollback of completed external effects.

## Worker and fan-out reliability

Events can be delivered repeatedly and invocations can time out after a side effect succeeded. Use idempotency keys and database unique constraints for logical jobs/findings, plus a separate idempotency identity for publishing externally. Preserve attempt events without duplicating logical results.

For parallel branches, declare each branch required or optional. Store branch status, completeness, source refs and policy version in the evidence package. Required branch failure means bounded retry or incomplete/inconclusive outcome. An optional failure can continue only when the finding clearly exposes the limitation.

Keep Step Functions state small—IDs, hashes, statuses and small summaries, not full diffs/documents. Store large immutable artifacts externally. Use bounded batches; do not create a Lambda invocation per file or model thought.

## LLM budgets and database scale

Enforce per-call and cumulative per-job input/output token, call-count, retry, spend and elapsed-time budgets. Add per-workspace and global concurrency controls. Reconcile actual usage per attempt, and preserve spend accounting through failure/cancellation/replay. Alert on budget rejection, unexpected cost, throttling, validation spikes and queue/dispatch age.

Avoid database connection storms under Lambda concurrency. Pick bounded pools/connection strategy from measured limits; evaluate RDS Proxy if connection pressure justifies it. Database constraints and transaction boundaries should enforce idempotency, uniqueness and state transitions wherever practical. Use expand/contract schema migration strategies and test rollback/compatibility.

## Publication and human review

High-impact, ambiguous or insufficiently supported findings require review under policy. Persist reviewer identity, time, exact finding version, disposition and rationale. Before publishing, recheck that cited source versions remain those analyzed and that freshness policy permits publication. Escape Markdown/HTML and enforce publication idempotency.

## Observability and recovery

Trace ingress → dispatch → workflow → stage → database/provider → validation → publication. Log opaque IDs, stage/attempt, duration, status, retryability, model/prompt/schema versions, token usage and safe request IDs. Do not put private source, full prompts/responses, API keys or high-cardinality IDs in metric labels.

Minimum alerts/runbooks:
- pending/old dispatch intents and workflow-start errors;
- workflow backlog, throttles, repeated failures and expired jobs;
- database connection saturation and migration incompatibility;
- model quota/cost spikes, token-budget denial, provider outage and invalid-output spikes;
- source freshness failures, duplicate side effects and publication conflict;
- safe replay/reconciliation, cancellation race, provider recovery and audit retrieval.

Start advisory/shadow-only. Do not enable AI-only merge blocking until policy is explicit and representative pilot evaluation demonstrates an approved quality threshold.

## Verification checklist

- [ ] DB commit/workflow-start failure injection and reconciliation.
- [ ] Duplicate request/event, duplicate stage and publication replay.
- [ ] Retry exhaustion, timeout after external success, cancellation/fencing race.
- [ ] Required vs optional branch failure policy.
- [ ] Token/call/spend reservation under parallelism and retries.
- [ ] Cross-tenant authorization for reads, cancel, evidence dereference and publish.
- [ ] Source freshness check at review/publication time.
- [ ] Secret/source redaction tests for logs/traces/errors.
- [ ] Runbook and alert tested in a sandbox before production.
`;export{e as default};
