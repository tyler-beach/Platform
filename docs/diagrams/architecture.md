# Architecture diagrams

## 1. System context

~~~mermaid
flowchart TB
  subgraph Sources["Source systems"]
    GH["Git repository / pull request"]
    SPEC["Technical specification"]
    ADR["ADRs / decision records"]
  end
  IN["Ingress API / event adapter"]
  SF["AWS Step Functions\nTop-level job state"]
  NORM["Go normalization workers"]
  RET["Go context retrieval"]
  STATIC["Go deterministic analysis\nDiff / AST / rules"]
  PACK["Evidence package builder"]
  AI["Go Anthropic adapter\nDirect Anthropic API"]
  VERIFY["Go validation + selective verifier"]
  DB[("Aurora PostgreSQL\nmetadata, jobs, findings")]
  S3[("S3\nsource snapshots / large artifacts")]
  OUT["API / review queue / repository result"]
  OBS["Logs, metrics, traces, audit"]
  GH --> IN
  SPEC --> IN
  ADR --> IN
  IN --> SF
  SF --> NORM
  NORM --> RET
  NORM --> STATIC
  RET --> PACK
  STATIC --> PACK
  GH -. immutable source .-> S3
  SPEC -. immutable source .-> S3
  ADR -. immutable source .-> S3
  PACK --> AI
  AI --> VERIFY
  VERIFY --> DB
  SF <--> DB
  VERIFY --> OUT
  NORM -. telemetry .-> OBS
  RET -. telemetry .-> OBS
  STATIC -. telemetry .-> OBS
  AI -. telemetry .-> OBS
  VERIFY -. telemetry .-> OBS
~~~

## 2. Analysis pipeline

~~~mermaid
flowchart TD
  A["Receive request / event"] --> B["Authorize + idempotency"]
  B --> C["Create AnalysisJob"]
  C --> D["Resolve immutable artifact versions"]
  D --> E["Normalize inputs"]
  E --> F1["Resolve candidate/applicable ADRs"]
  E --> F2["Deterministic code/document analysis"]
  F1 --> G["Build evidence package"]
  F2 --> G
  G --> H["Bounded Anthropic assessment"]
  H --> I["Schema + semantic validation"]
  I --> J{"Evidence and policy checks pass?"}
  J -- No --> K["Inconclusive / bounded recovery"]
  J -- Yes --> L{"Ambiguous or high-impact?"}
  L -- Yes --> M["Independent verification"]
  L -- No --> N["Persist findings/result"]
  M --> O{"Evidence supported?"}
  O -- Yes --> N
  O -- No --> P["Needs human review"]
  K --> N
  P --> N
  N --> Q["Publish advisory result"]
~~~

## 3. Sequence

~~~mermaid
sequenceDiagram
  participant Client
  participant API as Go Ingress
  participant SF as Step Functions
  participant W as Go Workers
  participant DB as PostgreSQL
  participant A as Anthropic
  Client->>API: Submit change + source version
  API->>DB: Create job / idempotency check
  API->>SF: Start execution(job_id)
  SF->>W: Normalize artifacts
  W->>DB: Persist metadata and evidence refs
  par Context retrieval
    SF->>W: Resolve applicable decisions
    W->>DB: Query status/scope/relationships
  and Deterministic analysis
    SF->>W: Parse diff / symbols / rules
    W-->>SF: Static evidence
  end
  SF->>W: Assemble bounded evidence package
  W->>A: Structured assessment request
  A-->>W: Candidate finding
  W->>W: Validate schema, refs and source version
  opt Verification required
    SF->>W: Verify candidate
    W->>A: Bounded challenge request
    A-->>W: Verification result
  end
  SF->>DB: Persist result and audit events
  SF-->>API: Job status / result reference
  API-->>Client: Result or job URL
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
  CODE["Code change / implementation"] --- IADR["Implementation ↔ ADR"]
  ADR1["Applicable decision"] --- IADR
  SPEC1["Technical specification"] --- SADR["Specification ↔ ADR"]
  ADR2["Applicable decision"] --- SADR
  SPEC2["Technical specification"] --- SIMP["Specification ↔ implementation"]
  CODE2["Implementation evidence"] --- SIMP
~~~

## 6. Failure handling

~~~mermaid
stateDiagram-v2
  [*] --> Queued
  Queued --> Running
  Running --> Running: bounded retry for transient error
  Running --> NeedsReview: ambiguous or evidence incomplete
  Running --> Succeeded: valid result persisted
  Running --> Failed: non-retryable error / retry budget exhausted
  Running --> Cancelled: cancellation
  NeedsReview --> Succeeded: disposition recorded
  NeedsReview --> Failed: review expired by policy
  Succeeded --> [*]
  Failed --> [*]
  Cancelled --> [*]
~~~

The diagrams express the proposed architecture. Confirm service limits, IAM design, data flow and deployment specifics during implementation.
