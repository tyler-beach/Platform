# Workflow operations and reliability

## Ownership boundaries
- **gRPC API service (if deployed):** synchronous job-control operations, request validation, authentication/authorization, idempotent job creation and read endpoints.
- **Step Functions:** overall async job state, branches, retries, catch paths, deadlines and approval waits.
- **Go Lambda workers:** bounded operations such as normalization, retrieval, deterministic checks, assessment, verification and persistence.
- **Database:** authoritative job/result/audit state; workflow execution history is operational context, not the only long-term audit record.

Do not have the gRPC API execute the entire analysis inline. Create a job, start the workflow, return its ID, then expose status/results. Do not make each Lambda a gRPC server.

## Suggested workflow
1. Authenticate/authorize and validate request.
2. Create job with an idempotency key and immutable source version references.
3. Normalize artifact metadata.
4. Run independent retrieval and deterministic analysis branches in parallel where useful.
5. Aggregate evidence and deduplicate candidate findings.
6. Call Anthropic for a bounded structured assessment.
7. Validate schema, evidence refs, versions, applicability and deterministic rules.
8. Conditionally verify ambiguous/high-impact findings.
9. Persist result/provenance.
10. Publish advisory result or route for human review; record terminal status.

Use bounded batches; do not create a Lambda per file or model thought.

## RPC reliability
- Propagate caller deadlines and cancellation; set server-side maximums.
- Set maximum inbound/outbound message sizes and page sizes.
- Use TLS and enforce authenticated identity plus repository/workspace authorization.
- Return documented standard gRPC status codes.
- Health-check the server; implement graceful shutdown and safe rolling deploys.
- Add request, trace and job IDs to logs/metrics; do not log source code, tokens or raw secrets.
- Require an idempotency key for CreateAnalysisJob. A client retry after lost response must not launch duplicate workflows.
- Don't assume deadline cancellation rolls back an already-completed side effect.
- A gRPC API hosted on ECS/Fargate behind an ALB adds always-on cost, scaling/network configuration and deployment operations. Review whether actual consumers justify it.

## Step Functions and worker reliability
Events may be delivered more than once. Derive idempotency identity from event ID plus immutable source versions and pipeline/policy version. Replays should not create duplicate findings/comments.

Use bounded retries with jitter for transient connectivity/5xx and throttling, honoring downstream retry hints. Don't blindly retry authorization failures, invalid requests, unsupported inputs, stale evidence, or deterministic validation failures. Retry budgets must not reset token/cost/job deadlines. Persist typed failure and diagnostic correlation ID after exhaustion.

Limit model concurrency globally and by workspace. Avoid exhausting PostgreSQL with Lambda-created pools; size connection behavior for expected concurrency. Add SQS/EventBridge when buffering/distribution is needed, not by default.

## Human review and freshness
High-impact, ambiguous or low-evidence findings require review. Store reviewer, timestamp, exact finding version, disposition and rationale. Recheck source freshness before publishing if source changed during analysis/review.

## Reliability checklist
- Duplicate-event and idempotency tests.
- RPC auth, deadline, status and message-size tests if RPC is deployed.
- Bounded retries and explicit terminal failures.
- Safe operator replay.
- Parallel-branch partial failure policy.
- Source freshness before publication.
- Model concurrency/token/cost budget enforcement.
- Trace IDs across RPC, workflow, workers and provider calls.
- Alerts for API availability, workflow failures, provider errors, validation spikes, backlog and unexpected spend.
- Runbooks for gRPC service rollout/health, provider failure, DB connectivity and schema incompatibility.

Start in advisory/shadow mode. Enable enforcement only after quality has been measured and policy approved.


## Functional and replay safety

Pure transformations may be retried safely when their explicit inputs/policy versions are unchanged. Effectful operations (job creation, workflow start, model invocation, persistence and publication) need operation identity, budgets and idempotency semantics. Do not promise exactly-once execution. Stable-sort evidence and finding collections before hashing or serializing. Preserve attempts as audit metadata without mutating source artifacts used by previous attempts.
