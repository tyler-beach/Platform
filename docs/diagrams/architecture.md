# Architecture diagram catalog

This page links to the scalable SVG diagrams and provides the state/data models. Each diagram is versioned beside the documentation and represents the **proposed target**, not deployed components.

## System architecture

![Layered reference architecture.](../assets/diagrams/system-architecture.svg)

The architecture separates authenticated ingress, durable asynchronous orchestration, bounded Go workers, persistent business data and external model access. One owner controls job lifecycle; model output is validated by application policy before durable publication.

## End-to-end analysis workflow

![Analysis workflow and control gates.](../assets/diagrams/analysis-workflow.svg)

The most important control gates are durable dispatch intent, immutable input pinning, evidence-branch completeness, preflight budget admission, application validation, atomic result persistence and freshness-safe publication.

## OpenSpec and test-driven engineering

![OpenSpec-first engineering lifecycle.](../assets/diagrams/engineering-loop.svg)

Requirement-to-scenario-to-test traceability is part of the acceptance record. Specs validate structure; tests and evaluations validate behavior.

## AI token budget and usage accounting

![Token and spend budget flow.](../assets/diagrams/token-budget.svg)

The job's total budget includes all attempts, retries, repair requests and optional verification. Output tokens are reserved before each call.

## Logical data relationships

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

This is logical only. It does not dictate physical table layout. Production DDL must include tenant-scoped keys, unique/idempotency constraints, migration strategy, retention and query/index validation.

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
  CancelRequested --> Succeeded: effect already committed; reconcile truth
  Running --> Expired: deadline exhausted
  NeedsReview --> Succeeded: disposition recorded
  NeedsReview --> Failed: reviewer rejects/terminates
~~~

The actual allowed transitions and cancellation race semantics must be implemented with durable state checks/fencing. A late external side effect cannot be pretended away; it remains auditable.
