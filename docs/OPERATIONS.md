# Workflow operations and reliability

## Orchestration ownership
AWS Step Functions is the recommended top-level distributed workflow owner. It coordinates reusable Go Lambda workers and manages state transitions, branches, retries, deadlines and approval waits. The database is the authoritative domain/audit store; workflow history is operational evidence, not the only persistent record.

## Suggested workflow
1. Authorize request and validate payload.
2. Create job with idempotency key and immutable source-version references.
3. Normalize artifact metadata.
4. Run independent work in parallel where useful: deterministic code/document analysis and contextual decision retrieval.
5. Aggregate/deduplicate candidates into an evidence package.
6. Call Anthropic for a bounded structured assessment.
7. Validate output, source references, applicability and deterministic rules.
8. Conditionally verify ambiguous/high-impact findings.
9. Persist result and provenance.
10. Publish advisory result or route for review; record terminal state.

Do not create a Lambda for every file or model thought. Use bounded batches and measured concurrency.

## Idempotency
Events may be delivered more than once. Derive idempotency identity from event ID plus immutable source versions and policy/pipeline version. Replays should reuse or safely recompute jobs, not create duplicate findings or repeated pull-request comments.

A finding dedupe key may include workspace, comparison mode, decision/rule ID, target artifact version and normalized finding category. Do not merge solely because two explanations sound similar.

## Retries and timeouts
Use bounded retries with jitter for transient connectivity/5xx and throttling; honor provider guidance. Do not blindly retry authorization errors, invalid requests, unsupported formats, stale evidence requiring resubmission, or deterministic validation failure. Set both per-stage timeouts and an overall deadline. Retries must not reset total token/cost/call budget.

On retry exhaustion, persist a typed failure and diagnostic correlation ID. Avoid putting source snippets or provider response bodies into generic notifications.

## Concurrency/backpressure
Limit concurrent model calls globally and per workspace. Add SQS/EventBridge when queueing, buffering or event routing is needed, not by default. Avoid exhausting PostgreSQL with Lambda-created connection pools; model expected concurrency and use an appropriate managed connection approach.

## Human review
High-impact, ambiguous, low-evidence or policy-selected findings require review. Store reviewer, timestamp, exact finding version, disposition and rationale. Approval waits need expiration/timeout behavior, and should recheck source freshness if source changes during review.

## Reliability checklist
- Duplicate-event and idempotency tests.
- Error classification and bounded retries.
- Failed-job handling and safe operator replay.
- Job and stage deadlines.
- Stable job/trace IDs.
- Partial parallel-branch failure policy.
- Source freshness check before publishing.
- Concurrency/token/cost budget enforcement.
- Alerts for provider outage, validation spikes, backlog, failure and unusual spend.
- Runbooks for provider failures, DB/connectivity issues, failed executions and regressions.

Start in advisory/shadow mode. Enable enforcement only after quality has been measured and policy has been approved.
