# API contract: first pass

**Status:** Proposed v1 design. The service and REST gateway are not implemented yet. This page defines intended behavior for server, worker, CLI and integrations.

## Sources of truth

- The Protobuf file at proto/adrplatform/v1/platform.proto is authoritative for typed gRPC control-plane contracts.
- openapi.yaml is the proposed REST/JSON façade for Swagger UI and future HTTP adapters. JSON property naming follows protobuf JSON mapping.
- CONTRACTS.md, EVIDENCE.md, and LOGGING_AND_AUDIT.md define semantic invariants beyond schema.
- Generate transport types from checked-in schemas; do not hand-maintain parallel DTOs. Internal persistence types may be richer than public messages; do not expose DB rows wholesale.

## v1 operations

| HTTP operation | Purpose | Protobuf operation |
|---|---|---|
| POST /v1/workspaces/{workspaceId}/analysis-jobs | Idempotently create/accept async job | CreateAnalysisJob |
| GET /v1/workspaces/{workspaceId}/analysis-jobs/{jobId} | Get authorized job state | GetAnalysisJob |
| POST /v1/workspaces/{workspaceId}/analysis-jobs/{jobId}:cancel | Request cancellation | CancelAnalysisJob |
| GET /v1/workspaces/{workspaceId}/analysis-jobs/{jobId}/findings | List findings with opaque pagination | ListFindings |
| GET /v1/workspaces/{workspaceId}/findings/{findingId} | Get finding and evidence references | GetFinding |

Routes are proposed mappings, not proof of a running REST endpoint. Do not publish a real server URL until ingress and authentication are implemented.

## Create job semantics

A request provides workspace, idempotency key, comparison mode and immutable artifact references. The server authenticates and authorizes; validates input source versions/cardinality; canonicalizes the request; persists job plus idempotency state; safely starts or schedules the workflow; then returns 202 Accepted with a job ID.

Same workspace + idempotency key + same canonical request returns the original job with reusedExistingJob=true. Same key with different canonical request returns 409 IDEMPOTENCY_KEY_REUSED. Retain idempotency records at least as long as the supported client retry window; ratify exact retention before production.

## Asynchronous lifecycle

Creation does not wait for analysis. Clients poll GetAnalysisJob or use a future notification mechanism. Acceptance does not imply findings exist.

Terminal execution states: SUCCEEDED, FAILED, CANCELLED, EXPIRED. NEEDS_REVIEW indicates policy-controlled human review. Implementation must explicitly define orchestration completion semantics for NEEDS_REVIEW without masking technical failure.

Cancellation is best-effort: accepted means the request was accepted, not that completed model calls, writes or publication were rolled back.

## Pagination

- pageSize zero or omitted selects server default; reject invalid negative values and clamp oversized values to the maximum.
- pageToken is opaque, integrity-protected, bounded, and scoped to workspace/job/query filters.
- Tokens are not authorization. Authorize each request independently.
- Stable ordering should use createdAt then findingId over a fixed result snapshot where feasible.
- Return empty nextPageToken when no next page exists.
- Invalid/expired token produces stable invalid-argument error; client restarts pagination rather than parsing tokens.

## Error/status mapping

| HTTP | Stable code / meaning | gRPC analogue | Retry guidance |
|---:|---|---|---|
| 400 | INVALID_ARGUMENT | INVALID_ARGUMENT | Fix request; do not retry unchanged |
| 401 | UNAUTHENTICATED | UNAUTHENTICATED | Refresh credentials, then retry once |
| 403 | PERMISSION_DENIED | PERMISSION_DENIED | No, unless access policy changes |
| 404 | NOT_FOUND; may conceal unauthorized resource | NOT_FOUND | No |
| 409 | CONFLICT / IDEMPOTENCY_KEY_REUSED / invalid state | ALREADY_EXISTS or FAILED_PRECONDITION | Resolve conflict first |
| 429 | RATE_LIMITED / budget exceeded | RESOURCE_EXHAUSTED | Bounded retry; honor server guidance |
| 500 | INTERNAL | INTERNAL | Retry only if operation is safe |
| 503 | DEPENDENCY_UNAVAILABLE | UNAVAILABLE | Bounded retry with jitter/deadline |
| 504 | DEADLINE_EXCEEDED | DEADLINE_EXCEEDED | Retry only with safe idempotency |

HTTP errors use RFC 9457 Problem Details plus stable code, requestId, retryable and bounded violations. Never disclose whether hidden resources exist in another workspace.

## Authentication and authorization

The API requires authenticated identity and server-side workspace authorization. Workspace IDs, artifact IDs, source URIs, repository names and pagination tokens are selectors, not access grants. TLS is required outside local development. Every read, cancellation, listing, evidence dereference and publication checks authorization at point of use. Choose a concrete auth design before production: user OIDC/service identity, token audience, roles/scopes, rotation, and audit actor mapping. Configure request/message sizes, quotas, deadlines and rate limits at ingress and server boundaries.

## Compatibility and versioning

- Public HTTP prefix is /v1; Protobuf package is adrplatform.v1.
- Prefer additive fields/RPCs. Never renumber/reuse Protobuf field numbers or enum numbers; reserve removed names and numbers.
- Do not change enum meaning in place. Add values and define behavior for old clients.
- Unknown outcome/status must not silently map to a safe-looking value.
- Review OpenAPI and Proto together. CI should run buf lint, buf build, buf breaking, OpenAPI lint and validation that REST DTOs map to intended protobuf messages.
- Schema files are authoritative; generated code is derived. Keep contracts, migration compatibility and docs aligned to a release.
- Compatibility break requires a new version/package or explicit migration plan.

## Out of initial v1

Artifact upload/ingestion, decision/requirement CRUD, source registration, review submission, evidence excerpt retrieval, webhook subscriptions, streaming progress, and publication/check-comment endpoints are not part of the initial API. ModelRun, AuditEvent, Requirement, Decision and Relationship are internal domain/persistence contracts until access patterns and authorization rules are reviewed.

## Implementation checklist

- [ ] Confirm whether HTTP façade or gRPC is the first deployed boundary.
- [ ] Authenticate and authorize every operation.
- [ ] Validate idempotency and workflow-start failure recovery.
- [ ] Define deadlines, quotas, size limits and state transitions in code.
- [ ] Generate server/client types.
- [ ] Validate evidence IDs/versions before persistence/publication.
- [ ] Test enums, pagination, error codes and authorization.
- [ ] Run Proto lint/build/breaking and OpenAPI validation in CI.
- [ ] Publish docs from same commit as schema changes.
