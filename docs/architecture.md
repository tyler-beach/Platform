# Architecture and system design

<span class="page-eyebrow">SYSTEM DESIGN</span>

The platform compares implementation and technical specifications with architectural decisions. Its design separates request admission, durable orchestration, deterministic evidence collection, model assessment, validation and review.

## AWS deployment architecture

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../assets/diagrams/system-architecture.svg" alt="AWS deployment architecture with service icons, account and VPC boundaries, API Gateway, Step Functions, Go Lambda stages, Aurora PostgreSQL, optional S3, IAM, KMS, Secrets Manager, CloudWatch, CloudTrail, controlled egress and Anthropic API." /></div>
  <figcaption>Service placement, request and data flow, network boundaries, and the direct provider integration.</figcaption>
</figure>

## Trust boundaries and data handling

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../assets/diagrams/trust-boundaries.svg" alt="Trust-boundary diagram for untrusted code and ADR sources, authenticated API admission, Step Functions and scoped worker roles, durable evidence validation, direct Anthropic processing and publication controls." /></div>
  <figcaption>Authorization stays in the application. Source text is untrusted, model output is a candidate, and validated findings retain exact source provenance.</figcaption>
</figure>

## Runtime profiles

| Profile | Use when | Main trade-off |
|---|---|---|
| HTTP/API Gateway with Go Lambda and Step Functions | Webhooks and asynchronous API consumers are sufficient for the first slice | Simple ingress; manage Lambda concurrency and database connections |
| gRPC control plane on ECS/Fargate behind an HTTPS ALB | A named client needs long-lived gRPC semantics | Adds service rollout, health management and always-on cost |
| Shared data plane | Either profile | Aurora owns job and result metadata; S3 holds large immutable artifacts where needed |

Protobuf can remain the contract source even when the first API is HTTP/JSON. Lambda workers execute tasks; they do not host gRPC listeners. The model provider is the direct Anthropic API, behind a typed Go adapter.

The deployment choice between HTTP/Lambda and a long-lived gRPC service, along with the egress route used for provider calls, should be settled before those boundaries are implemented.

## Analysis workflow

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../assets/diagrams/analysis-workflow.svg" alt="Six-stage workflow: admit and authorize, pin source versions, gather deterministic evidence, reserve cumulative budget, run a bounded assessment, validate and persist the outcome, then apply freshness and review gates." /></div>
  <figcaption>One workflow owns stage ordering, retries, deadlines and cancellation. Required-evidence gaps remain visible in the outcome.</figcaption>
</figure>

Key invariants:

1. **Durable acceptance.** Commit the job, idempotency record and dispatch intent before acknowledging. Reconcile workflow-start failures so accepted jobs do not become stranded.
2. **Pinned evidence.** Preserve source revisions, content hashes and the parser, pipeline and policy versions used.
3. **Visible completeness.** Every evidence branch reports status and completeness. Missing required evidence triggers bounded recovery or an inconclusive result.
4. **Shared budget.** Retries, repairs and verification consume the same token, spend, call and deadline allowances.
5. **Validated persistence.** Go code validates source versions, evidence IDs, applicability and domain rules before committing findings.
6. **Fresh publication.** Persist the result first, then recheck source freshness and review policy before any external effect.

## Budget and usage accounting

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../assets/diagrams/token-budget.svg" alt="Budget flow from request construction and token estimation through concurrency-safe reservation, bounded provider execution, usage reconciliation and stop conditions across a shared job ledger." /></div>
  <figcaption>Per-call limits are combined with a cumulative per-job ledger shared across parallel work, retries and optional verification.</figcaption>
</figure>

The price/model settings and prompt/schema versions are recorded as configuration, not embedded as domain constants. Ambiguous provider usage remains accounted for conservatively until reconciled.

## Engineering delivery

<figure class="diagram-figure">
  <div class="diagram-viewport"><img src="../assets/diagrams/engineering-loop.svg" alt="OpenSpec lifecycle from proposal and behavioral scenarios through regression proof, implementation, layered verification, adversarial review and archive." /></div>
  <figcaption>Archive follows verification evidence and review—not code completion alone.</figcaption>
</figure>

## Ownership by concern

| Concern | Owner | Rule |
|---|---|---|
| Identity and workspace scope | Ingress and server-side authorization | A caller-supplied workspace ID is only a selector |
| Asynchronous job lifecycle | Step Functions plus durable job/dispatch state | No competing orchestrator |
| Domain policy | Pure Go functions over explicit, versioned inputs | Prompts and workflow expressions do not own policy |
| Model calls | Typed harness | Enforce budgets, deadlines, schema and retry rules |
| Provenance | Immutable artifact versions and evidence locators | Findings point to the exact inputs analyzed |
| Business audit | Durable job/review/audit records | Tracing is operational telemetry, not the business record |
| Publication | Validated application path | Freshness, authorization, review policy and idempotency must hold |

