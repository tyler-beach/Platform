# Architecture diagrams

<span class="page-eyebrow">SYSTEM MODELS</span>

These diagrams use the AWS Architecture Icons and scale to the available page width. Use the architecture page for the design rationale and component ownership.

## 01 · AWS deployment architecture

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../../assets/diagrams/system-architecture.svg" alt="AWS target deployment with account and VPC boundaries, service icons, worker stages, Aurora, optional S3, security controls, and direct Anthropic API egress." /></div>
  <figcaption>Service placement, network zones, data stores, security controls and provider egress.</figcaption>
</figure>

## 02 · Trust boundaries

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../../assets/diagrams/trust-boundaries.svg" alt="Trust boundaries from untrusted source inputs through authorization, scoped AWS execution, evidence validation, Anthropic processing and publication." /></div>
  <figcaption>Trust changes and the controls required at each crossing.</figcaption>
</figure>

## 03 · Analysis workflow

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../../assets/diagrams/analysis-workflow.svg" alt="Bounded analysis stages from admission and immutable source pinning through evidence collection, budget gate, assessment, validation, persistence and publication." /></div>
  <figcaption>Workflow state, evidence completeness, budgets and review gates.</figcaption>
</figure>

## 04 · Token and spend budget

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../../assets/diagrams/token-budget.svg" alt="Cumulative token, spend, call, retry, concurrency and deadline controls with atomic reservations and per-attempt usage reconciliation." /></div>
  <figcaption>One shared ledger is used by parallel calls, retries, repairs and verification.</figcaption>
</figure>

## 05 · Engineering lifecycle

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../../assets/diagrams/engineering-loop.svg" alt="OpenSpec delivery process from approved scope and behavior scenarios through test-first implementation, verification, adversarial review and archive." /></div>
  <figcaption>Requirements trace to tests, evaluation evidence and review decisions.</figcaption>
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

The logical relationships guide contract and persistence design. Tenant-scoped keys, uniqueness and idempotency constraints, migrations, retention and query/index behavior still need verification during implementation.

## Job lifecycle

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

Cancellation is best-effort. Record late effects and fence late worker commits; never describe cancellation as rollback of work already completed.
