# Architecture diagram catalog

<span class="page-eyebrow">REFERENCE LIBRARY / SYSTEM MODELS</span>

The SVGs below are maintained with the design contracts. They are intentionally displayed at a readable engineering-diagram scale inside horizontally scrollable frames. They represent target architecture, not resources currently deployed.

## 01 / System architecture

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../../assets/diagrams/system-architecture.svg" alt="Reference system architecture showing source systems, trusted ingress, Step Functions, Go workers, persistence and external services." /></div>
  <figcaption>Component boundaries, trust zones, data ownership and provider integration.</figcaption>
</figure>

## 02 / Analysis workflow

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../../assets/diagrams/analysis-workflow.svg" alt="Analysis workflow from authorized job creation to evidence collection, bounded assessment, validation, persistence and review." /></div>
  <figcaption>Admission, completeness, budget, validation and publication gates.</figcaption>
</figure>

## 03 / Engineering loop

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../../assets/diagrams/engineering-loop.svg" alt="OpenSpec-first delivery cycle including behavior scenarios, RED-GREEN-REFACTOR, layered tests, adversarial review and archive." /></div>
  <figcaption>Traceability from requirements through executable acceptance evidence.</figcaption>
</figure>

## 04 / Token budget

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../../assets/diagrams/token-budget.svg" alt="Token and spend control flow including preflight, output reservation, job caps, usage reconciliation and stop conditions." /></div>
  <figcaption>Cumulative model budget enforcement across concurrent calls and retries.</figcaption>
</figure>

## Logical domain relationships

~~~mermaid
erDiagram
  WORKSPACE ||--o{ ARTIFACT : contains
  ARTIFACT ||--o{ ARTIFACT_VERSION : versions
  ARTIFACT_VERSION ||--o{ REQUIREMENT : yields
  ARTIFACT_VERSION ||--o{ EVIDENCE_ITEM : source_of
  WORKSPACE ||--o{ ANALYSIS_JOB : owns
  ANALYSIS_JOB ||--o{ MODEL_RUN : records
  ANALYSIS_JOB ||--o{ FINDING : produces
  FINDING ||--o{ FINDING_EVIDENCE : cites
  EVIDENCE_ITEM ||--o{ FINDING_EVIDENCE : supports
  FINDING ||--o{ REVIEW : receives
  ANALYSIS_JOB ||--o{ AUDIT_EVENT : records
  ANALYSIS_JOB ||--o{ BUDGET_RESERVATION : accounts_for
~~~

This logical view does not dictate the physical table layout. Production DDL still needs tenant-scoped keys, unique/idempotency constraints, migrations, retention and query/index validation.

## Job execution states

~~~mermaid
stateDiagram-v2
  [*] --> Accepted
  Accepted --> DispatchPending
  DispatchPending --> Queued: dispatch confirmed
  DispatchPending --> DispatchPending: reconcile / retry
  Queued --> Running
  Running --> Running: bounded retry
  Running --> NeedsReview: policy requests review
  Running --> Succeeded: validated result committed
  Running --> Failed: non-retryable or exhausted
  Running --> CancelRequested
  CancelRequested --> Cancelled: no further effects allowed
  CancelRequested --> Succeeded: effect committed; reconcile truth
  Running --> Expired: deadline exhausted
  NeedsReview --> Succeeded: disposition recorded
  NeedsReview --> Failed: reviewer rejects/terminates
~~~

The actual transitions and cancellation-race semantics must be implemented with durable checks/fencing. A late external side effect cannot be hidden; it remains auditable.
