# Architecture and system diagrams

This describes the recommended target, not a claim that components are deployed.

## System context

~~~mermaid
flowchart TB
  C[Engineer / CI / Integration] --> I[Authenticated API boundary]
  I --> J[(PostgreSQL: Jobs and Idempotency)]
  I --> O[Workflow start / outbox]
  O --> SF[Step Functions]
  SF --> N[Normalize source]
  SF --> D[Deterministic checks]
  SF --> R[Retrieve ADRs and requirements]
  N --> E[Evidence package]
  D --> E
  R --> E
  E --> H[Go assessment harness]
  H --> A[Anthropic API]
  A --> V[Application schema + semantic validation]
  V --> F[(PostgreSQL: Findings and provenance)]
  F --> API[Job / finding query API]
  V --> HR[Human review when required]
  HR --> AU[(Review and audit records)]
  SF -. large immutable artifacts .-> S3[(S3, optional)]
  I -. request/trace context .-> OT[OpenTelemetry]
  SF -. execution telemetry .-> OT
  H -. usage and validation metrics .-> OT
~~~

## Asynchronous job sequence

~~~mermaid
sequenceDiagram
  autonumber
  participant Client
  participant API
  participant DB as PostgreSQL
  participant SF as Step Functions
  participant W as Go Lambda workers
  participant LLM as Anthropic API
  Client->>API: Create job + idempotency key
  API->>DB: Authorize, validate, insert job + idempotency
  API->>SF: Start or enqueue workflow idempotently
  API-->>Client: 202 Accepted + job ID
  SF->>W: Normalize / retrieve / deterministic checks
  W->>DB: Read authorized immutable versions
  W-->>SF: Evidence package references
  SF->>W: Bounded assessment
  W->>LLM: Structured assessment request
  LLM-->>W: Candidate structured output
  W->>W: Validate schema, versions, IDs and policy
  W->>DB: Persist finding + model run + audit events
  Client->>API: Get job / list findings
  API->>DB: Authorize and read snapshot
  API-->>Client: Status / findings / references
~~~

## Trust boundaries

~~~mermaid
flowchart LR
  U[Untrusted ADRs / code / specs] --> P[Bounded parsers and source adapters]
  P --> E[Evidence package with provenance]
  E --> M[Model: source is data, not instructions]
  M --> V[Schema and semantic validator]
  V --> S[Authorized persistence]
  S --> PUB[Optional publication after freshness and policy checks]
  AUTH[Authenticated identity + workspace policy] --> P
  AUTH --> S
  GUARD[No model-controlled shell, secrets, or writes] -. constrains .-> M
~~~

## State ownership

- **API service:** authentication/authorization, request validation, idempotent job creation and queries.
- **Step Functions:** distributed stages, retries, catch paths, deadlines and execution flow.
- **Go Lambda workers:** reusable bounded operations; no gRPC listener inside ordinary Lambda.
- **PostgreSQL:** authoritative job/result/review/audit records.
- **S3 (optional):** large immutable artifacts subject to retention.
- **OpenTelemetry:** operational correlation, not authoritative audit.
- **Anthropic:** external model operation behind a typed Go harness; model output is untrusted candidate data.

A webhook-only/serverless HTTP boundary can come before a long-lived gRPC server if consumers do not yet justify ECS/Fargate. See [RPC and Protobuf design](RPC_AND_PROTOBUF.md).
