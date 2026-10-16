# Architecture overview

## Recommended target

Use a Go-first, evidence-driven service. The revised communication design is contract-first Protobuf with a gRPC control-plane API where a long-lived synchronous API has a real consumer. Keep AWS Step Functions as the owner of asynchronous job execution and invoke bounded Lambda workers directly. The gRPC server, if included, is a long-lived Go service (candidate: ECS/Fargate behind an HTTPS Application Load Balancer), not a listener inside Lambda.

Use the Anthropic API directly through an adapter; do not route inference through Bedrock. Use PostgreSQL/Aurora PostgreSQL for authoritative metadata and results; S3 for immutable source snapshots/large artifacts when needed. Add pgvector only if retrieval evaluation demonstrates value.

The gRPC API deployment and always-on cost remain a decision to settle before MVP. A webhook-only MVP can use HTTP/Lambda ingress while retaining Protobuf as a schema discipline.

## Logical components

- **gRPC control-plane API (optional deployment profile):** authenticates callers, authorizes workspace/artifact references, validates requests, creates idempotent jobs, starts workflow executions and serves job/finding reads.
- **Ingress adapters:** GitHub webhooks and browser/third-party integrations may require HTTP/JSON adapters. These are separate protocol boundaries, not reasons to force all callers to gRPC.
- **Workflow orchestrator:** Step Functions owns multi-stage job state, branching, retry/catch, parallel work, deadlines and human-review waits.
- **Artifact normalization:** converts code changes, specs and ADRs into normalized, versioned artifacts while preserving source identity, hash, location, owner, status and revision.
- **Context retrieval:** resolves candidate decisions and requirements from status/scope/relationships, identifiers, symbols, full-text search and optionally semantic search.
- **Deterministic analysis:** parses diffs, syntax/AST/symbol relationships, supported document formats and explicit checks to create source-linked evidence.
- **Evidence package assembly:** prepares the smallest sufficient, budgeted package for one comparison mode.
- **AI assessment:** Go adapter calls Anthropic directly with a versioned prompt/schema, deadline, token/cost limits and typed errors.
- **Verification:** checks schema, evidence IDs, source versions, applicability and domain invariants; optional independent model review is selective.
- **Persistence/delivery:** records jobs, artifacts, findings, run metadata, audit events and reviewer dispositions.

## Communication patterns

- Use **gRPC + Protobuf** for synchronous, strongly typed control-plane calls between clients and a long-lived API service.
- Use **Step Functions service integrations** for workflow-to-Lambda task calls. Lambda tasks should not be gRPC servers.
- Use small JSON envelopes for Step Functions state. If shared Protobuf message types are used at that boundary, convert via ProtoJSON explicitly and test round-tripping.
- Use **SQS/EventBridge** only when buffering, fan-out or event distribution is needed.
- Use events/notifications for completion if polling becomes insufficient.
- Do not build synchronous gRPC calls for every internal function. In-process Go interfaces are enough until a real service boundary exists.

AWS ALB can route gRPC to registered instance/IP targets but cannot use Lambda as the gRPC target. Therefore, a genuine gRPC server means a long-lived service such as ECS/Fargate (or another always-running target). The alternative is HTTP/Lambda ingress for a serverless-only MVP. See docs/RPC_AND_PROTOBUF.md.

## Design patterns

- **Pipeline/stages:** one responsibility and typed input/output per stage.
- **Ports and adapters:** domain logic avoids AWS/provider-specific types.
- **Immutable artifacts/evidence:** source versions and stage outputs have stable IDs/hashes.
- **Contract-first API:** Protobuf is the source schema for the versioned gRPC control-plane API.
- **Explicit state machine:** job lifecycle and permitted transitions are explicit.
- **Fan-out/fan-in:** independent deterministic analysis and context retrieval can run in parallel.
- **Hybrid rules + AI:** deterministic checks for crisp predicates; model reasoning for semantic interpretation.
- **Idempotent workers:** retries/replays do not duplicate results or external side effects.
- **Append-oriented audit trail:** record transitions, retries, publishing and reviewer disposition.
- **Human-in-the-loop:** ambiguous/high-impact findings go to review.
- **Transactional outbox only if needed:** add when domain persistence and event publication consistency require it.

Avoid an unversioned global “blackboard” of changing text. Prefer persisted job state and immutable artifacts/evidence packages with explicit IDs and versions.

## Orchestration boundary

Step Functions owns the distributed analysis job. gRPC owns request/response operations at the synchronous API boundary. Neither replaces the other. Do not make gRPC the job orchestrator and do not use Step Functions plus LangGraph as competing owners of the same job lifecycle.

LangGraph is optional for a bounded AI sub-workflow if conditional reasoning loops/checkpointing become materially useful. It is not required to call functions or use non-LLM workers.

## Candidate AWS footprint

- **Serverless API profile:** API Gateway/HTTP + Go Lambda, Step Functions and Lambda workers; protobuf can remain the schema/contracts tool without running a gRPC server.
- **gRPC API profile:** HTTPS ALB + Go gRPC API on ECS/Fargate; API starts and queries Step Functions; worker Lambdas remain unchanged.
- **Shared data plane:** Aurora/PostgreSQL, S3 where needed, Secrets Manager, IAM, CloudWatch and OpenTelemetry-compatible tracing/export.
- Add SQS/EventBridge only when operationally needed.

## Failure policy

Workers return typed results or classified errors. Retry transient faults with bounded backoff; do not blindly retry invalid input, authorization failures, unsupported formats, stale references or deterministic validation failures. All jobs end as completed, review-required, failed, cancelled or expired. gRPC calls use deadlines, message-size limits and standard status codes. Creation is idempotent by key.

See docs/RPC_AND_PROTOBUF.md, docs/diagrams/architecture.md, docs/DATA_MODEL.md and docs/OPERATIONS.md.
