# Architecture diagrams

## 1. System context with gRPC control plane

~~~mermaid
flowchart TB
  subgraph Inputs["Sources and clients"]
    GH["GitHub webhook / repository"]
    SPEC["Technical specification"]
    ADR["ADRs / decision records"]
    CLIENT["Go clients / internal services"]
  end
  ALB["HTTPS ALB\nHTTP/2 + gRPC"]
  API["Go gRPC API\nECS/Fargate if selected"]
  AUTH["AuthN/AuthZ\nvalidation + idempotency"]
  DB[("Aurora PostgreSQL\njobs, findings, metadata")]
  SF["Step Functions\nasync job lifecycle"]
  L1["Go Lambda\nnormalize"]
  L2["Go Lambda\ncontext retrieval"]
  L3["Go Lambda\ndeterministic analysis"]
  L4["Go Lambda\nAnthropic assessment"]
  L5["Go Lambda\nverification + persistence"]
  A["Anthropic API direct"]
  S3[("S3\nimmutable artifact snapshots")]
  GH --> AUTH
  SPEC --> AUTH
  ADR --> AUTH
  CLIENT --> ALB --> API --> AUTH
  AUTH --> DB
  AUTH --> SF
  SF --> L1
  SF --> L2
  SF --> L3
  SF --> L4
  L4 --> A
  SF --> L5
  L1 --> DB
  L2 --> DB
  L3 --> S3
  L5 --> DB
~~~

Notes:
- The gRPC API is a long-lived service; it is not a Lambda listener.
- A webhook-only serverless MVP may replace the gRPC endpoint with HTTP/API Gateway + Lambda.
- Step Functions invokes worker Lambdas directly; don't insert gRPC between workflow and Lambda tasks.
- Protobuf schemas define the gRPC API; Step Functions data remains small JSON envelopes.

## 2. Analysis pipeline

~~~mermaid
flowchart TD
  A["Client / webhook"] --> B["Authenticate + authorize"]
  B --> C["Create idempotent AnalysisJob"]
  C --> D["Start Step Functions; return job ID"]
  D --> E["Resolve immutable artifact versions"]
  E --> F["Normalize inputs"]
  F --> G1["Resolve candidate/applicable ADRs"]
  F --> G2["Deterministic code/document analysis"]
  G1 --> H["Build evidence package"]
  G2 --> H
  H --> I["Bounded Anthropic assessment"]
  I --> J["Schema + semantic validation"]
  J --> K{"Evidence/policy checks pass?"}
  K -- No --> L["Inconclusive or bounded recovery"]
  K -- Yes --> M{"Ambiguous or high-impact?"}
  M -- Yes --> N["Selective independent verification"]
  M -- No --> O["Persist finding/result"]
  N --> O
  L --> O
  O --> P["Publish advisory result / review"]
~~~

## 3. Control-plane RPC and asynchronous workflow

~~~mermaid
sequenceDiagram
  participant Client
  participant API as Go gRPC API
  participant DB as PostgreSQL
  participant SF as Step Functions
  participant W as Go Lambda Worker
  participant A as Anthropic

  Client->>API: CreateAnalysisJob(idempotency key, artifact refs)
  API->>API: Authenticate + authorize
  API->>DB: Create or resolve job idempotently
  API->>SF: Start execution(job_id)
  API-->>Client: job_id + status (prompt response)
  SF->>W: Invoke worker via AWS integration
  W->>DB: Read authoritative metadata / persist stage
  W->>A: Structured request (assessment stage only)
  A-->>W: Candidate result
  W->>W: Validate schema/evidence references
  SF->>DB: Persist final state via worker
  Client->>API: GetAnalysisJob / ListFindings
  API->>DB: Read job/findings
  API-->>Client: Typed Protobuf response
~~~

## 4. Logical data model

~~~mermaid
erDiagram
  WORKSPACE ||--o{ ARTIFACT : contains
  ARTIFACT ||--o{ ARTIFACT_VERSION : versions
  ARTIFACT_VERSION ||--o{ REQUIREMENT : yields
  ARTIFACT_VERSION ||--o{ EVIDENCE_ITEM : referenced_by
  ARTIFACT ||--o{ RELATIONSHIP : source
  ARTIFACT ||--o{ RELATIONSHIP : target
  WORKSPACE ||--o{ ANALYSIS_JOB : owns
  ANALYSIS_JOB ||--o{ MODEL_RUN : invokes
  ANALYSIS_JOB ||--o{ FINDING : produces
  FINDING ||--o{ FINDING_EVIDENCE : cites
  EVIDENCE_ITEM ||--o{ FINDING_EVIDENCE : supports
  FINDING ||--o{ REVIEW : receives
  ANALYSIS_JOB ||--o{ AUDIT_EVENT : records
~~~

## 5. Three comparison modes

~~~mermaid
flowchart LR
  CODE["Implementation / code change"] --- IADR["Implementation ↔ ADR"]
  ADR1["Applicable decision"] --- IADR
  SPEC1["Technical specification"] --- SADR["Specification ↔ ADR"]
  ADR2["Applicable decision"] --- SADR
  SPEC2["Technical specification"] --- SIMP["Specification ↔ implementation"]
  CODE2["Implementation evidence"] --- SIMP
~~~

## 6. Failure lifecycle

~~~mermaid
stateDiagram-v2
  [*] --> Queued
  Queued --> Running
  Running --> Running: bounded retry for transient failure
  Running --> NeedsReview: ambiguous or evidence incomplete
  Running --> Succeeded: validated result persisted
  Running --> Failed: nonretryable / retries exhausted
  Running --> Cancelled: cancellation request accepted
  Running --> Expired: job deadline exceeded
  NeedsReview --> Succeeded: review disposition recorded
  Succeeded --> [*]
  Failed --> [*]
  Cancelled --> [*]
  Expired --> [*]
~~~
