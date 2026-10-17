# API contract: production target

**Status:** Production-target v1 contract. The API and REST gateway are planned for implementation; the repository currently contains the typed contract, REST mapping, and deterministic mock responses rather than a deployed service. Mockups are contract-shaped examples, not live responses.

## Sources of truth

- `proto/adrplatform/v1/platform.proto` is the authoritative schema for typed gRPC control-plane contracts.
- `docs/openapi.yaml` maps those types to the production-target REST/JSON façade.
- Data, evidence, logging/audit and lifecycle contracts specify semantic invariants beyond schema.
- Generate transport types from schemas; do not hand-maintain parallel DTOs or expose DB rows wholesale.

## v1 operations

| HTTP operation | Purpose | Protobuf operation |
|---|---|---|
| POST /v1/workspaces/{workspaceId}/analysis-jobs | Idempotently create/accept job | CreateAnalysisJob |
| GET /v1/workspaces/{workspaceId}/analysis-jobs/{jobId} | Read job state | GetAnalysisJob |
| POST /v1/workspaces/{workspaceId}/analysis-jobs/{jobId}:cancel | Request best-effort cancellation | CancelAnalysisJob |
| GET /v1/workspaces/{workspaceId}/analysis-jobs/{jobId}/findings | List findings | ListFindings |
| GET /v1/workspaces/{workspaceId}/findings/{findingId} | Read finding/evidence refs | GetFinding |

## Acceptance and idempotency

The request includes authorized workspace, idempotency key, comparison mode and immutable artifact references. The server authenticates/authorizes, validates sizes/versions/cardinality, creates a canonical request fingerprint, and transactionally writes the job, idempotency record and durable dispatch intent before returning 202.

- Same workspace + key + same canonical request returns the original logical job.
- Same workspace + key + different request returns 409 IDEMPOTENCY_KEY_REUSED.
- Dispatch intent survives process death and workflow-start failure. A dispatcher/reconciler retries start without duplicate logical work and uses fencing/claim ownership to prevent stale updates.
- Idempotency retention must exceed the supported client retry window; exact retention must be selected before production launch.

## Async lifecycle and cancellation

Creation does not wait for analysis. Clients poll state or use a future notification mechanism. Terminal execution states include SUCCEEDED, FAILED, CANCELLED and EXPIRED; NEEDS_REVIEW requires explicit orchestration semantics. Domain finding outcome is separate from job execution status.

Cancellation is best-effort. Acceptance means the cancellation request was stored, not that provider work, completed writes or publication were rolled back. Workers must check current state/fencing before effectful commits and publication. A late side effect remains auditable.

## Pagination

- Omitted/zero page size selects server default; negative values are invalid and oversized values are clamped/rejected according to documented API policy.
- Page token is opaque, bounded, integrity-protected and scoped to workspace/job/query filters. It is never authorization.
- Reauthorize every page request.
- Stable ordering uses createdAt + finding ID over a stable result view where feasible.
- Invalid/expired token yields a stable invalid-argument error.

## Error policy

| HTTP | Stable meaning | gRPC analogue | Retry guidance |
|---:|---|---|---|
| 400 | INVALID_ARGUMENT | INVALID_ARGUMENT | Fix request |
| 401 | UNAUTHENTICATED | UNAUTHENTICATED | Refresh credentials; bounded retry |
| 403 | PERMISSION_DENIED | PERMISSION_DENIED | No retry until access changes |
| 404 | NOT_FOUND; may conceal unauthorized resource | NOT_FOUND | No retry |
| 409 | CONFLICT / reused idempotency key / invalid state | ALREADY_EXISTS or FAILED_PRECONDITION | Resolve conflict |
| 429 | RATE_LIMITED / quota or budget exceeded | RESOURCE_EXHAUSTED | Honor retry hints and shared deadline |
| 500 | INTERNAL | INTERNAL | Retry only if safe |
| 503 | DEPENDENCY_UNAVAILABLE | UNAVAILABLE | Bounded retry with jitter |
| 504 | DEADLINE_EXCEEDED | DEADLINE_EXCEEDED | Retry only with idempotency |

HTTP errors use RFC 9457 Problem Details with stable code, requestId, retryability and bounded violations. Do not reveal the existence of hidden resources in another tenant.

## Authorization and input trust

Workspace IDs, repository names, source URIs, artifact IDs and page tokens are selectors, not access grants. Reauthorize every read, cancel, list, evidence dereference and publication. Use TLS outside local development, bounded payload sizes, rate/usage quotas and server-side deadlines. Decide production identity model, token audience/roles, rotation, tenant isolation, actor mapping and retention before launch.

Source artifact text and model output are untrusted. The model is not an authorization principal and cannot select unrestricted tools or write endpoints.

## Token/cost quota responses

Differentiate request-rate throttling from analysis budget exhaustion. Budget exhaustion should be a stable response/state, not retried automatically without a changed budget/policy. If an asynchronous job reaches its budget ceiling, stop further model calls and persist a typed reason plus usage accounting. A caller must not reset a job budget by retrying the HTTP operation.

## Compatibility and launch gates

- HTTP prefix is /v1; Protobuf package is adrplatform.v1.
- Prefer additive schema changes. Never reuse removed Protobuf field numbers/names; reserve removed values.
- Unknown enum/outcome values must not silently map to no-deviation/success.
- CI runs Buf lint/build/breaking checks, OpenAPI validation/lint and mapping tests for both contracts.
- Use expand/contract database migrations, with old/new-reader compatibility during rollout.
- Compatibility break requires a new API/protobuf version or reviewed migration plan.
- Before production launch, implement the service, authentication/authorization, persistence, idempotency/dispatch reconciliation, schema-generated transport types, and contract/integration tests. The mock response examples are intended as acceptance fixtures for that work.

## Out of initial v1

Artifact ingestion/registration, decision CRUD, review submission, evidence excerpt retrieval, webhook subscriptions, streaming progress, and publication/check-comment endpoints are not part of initial v1. ModelRun, AuditEvent, Requirement, Decision and Relationship remain internal until access and authorization needs are reviewed.
