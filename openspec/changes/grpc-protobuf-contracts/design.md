# Design: gRPC and Protobuf boundary

## Decision proposal
Use Protobuf as the contract-first schema for the platform API. Use gRPC for synchronous control-plane calls from clients to a long-lived Go API server if that deployment is approved. Keep full analysis asynchronous through Step Functions, which invokes Lambda workers directly.

## Deployment boundary
A gRPC server is a long-lived process and should not be hosted as a request listener inside ordinary Lambda execution. If deployed, use a Go container service (candidate: ECS/Fargate) behind an HTTPS Application Load Balancer configured for gRPC. ALB gRPC target groups use instance/IP targets rather than Lambda targets. This adds cost and infrastructure; a webhook-only MVP may instead use API Gateway + Lambda and defer the gRPC server while retaining Protobuf schema contracts.

## Request lifecycle
1. Client sends CreateAnalysisJob with workspace selector, idempotency key, comparison mode and immutable artifact references.
2. Server authenticates caller and authorizes access to every workspace/repository/artifact reference.
3. Server creates/resolves an idempotent job and starts Step Functions.
4. Server returns job ID/status without waiting for model analysis.
5. Client polls GetAnalysisJob/ListFindings or uses a future notification integration.
6. Cancellation is best-effort and state-dependent; it does not imply completed side effects are undone.

## Schema conventions
- Protobuf package and API version: adrplatform.v1.
- Generated Go package: github.com/tyler-beach/Platform/gen/go/adrplatform/v1.
- Every enum has a *_UNSPECIFIED zero value.
- Field numbers are immutable; reserve removed fields/names.
- Breaking changes are checked with Buf.
- Requests reference immutable artifacts instead of carrying large source content.
- workspace_id is an untrusted selector; authorization derives from authenticated identity and server policy.
- Transport DTOs map to domain structs; generated messages are not automatically the database model.

## Worker protocol
The async workflow uses Step Functions to invoke Lambda workers. Do not introduce synchronous gRPC between those Lambda tasks just to claim gRPC adoption. Worker payloads should be small JSON envelopes (or ProtoJSON mapped with protojson where it materially benefits contract sharing) carrying job IDs, version references, evidence IDs and bounded stage outcomes. Store large evidence and pass references. Add a specific RPC contract if an analysis component later becomes a long-lived reusable service.

## Operations and security
Require TLS, authentication and workspace/repository authorization. Propagate deadlines/cancellation; bound message sizes; map errors to standard gRPC status codes. CreateAnalysisJob needs idempotency semantics. Instrument latency, status and trace/job IDs without logging source or secrets. Production needs health checks, graceful shutdown, rollout compatibility and a documented schema-evolution policy.
