# Architecture and system design

<span class="page-eyebrow">SYSTEM DESIGN / REFERENCE</span>

The platform separates evidence collection, asynchronous orchestration, model assessment and authoritative result storage. The diagrams below are target designs: they show boundaries the implementation should preserve, not deployed infrastructure.

## System architecture

<figure class="diagram-figure">
  <div class="diagram-viewport">
    <img src="../assets/diagrams/system-architecture.svg" alt="Layered architecture: source systems flow through an authenticated API and durable dispatch into Step Functions, bounded Go workers, validated model assessment, PostgreSQL and optional S3, secrets and observability." />
  </div>
  <figcaption>01 · Component boundaries, data ownership and external-service integrations. Scroll horizontally to read the full diagram at presentation scale.</figcaption>
</figure>

### Runtime profiles

| Profile | Appropriate when | Cost / operational trade-off |
|---|---|---|
| Serverless-first: API Gateway/HTTP + Go Lambda + Step Functions + worker Lambdas | Initial webhook and asynchronous API consumers | Thin ingress, but plan for cold starts and database connection scaling |
| Long-lived gRPC control plane: HTTPS ALB + Go gRPC on ECS/Fargate | A real client needs long-lived gRPC semantics | Adds service deployment, health/rollout, scaling and always-on cost |
| Shared data plane: PostgreSQL/Aurora, S3 as needed, Secrets Manager, OpenTelemetry | Shared by either profile | Define tenancy, retention, migrations and connection strategy before production |

Protobuf can remain contract-first even if the first public endpoint is HTTP/JSON. Do not host a gRPC listener in ordinary Lambda workers. The current provider direction is direct Anthropic API behind a typed Go harness.

## End-to-end analysis workflow

<figure class="diagram-figure">
  <div class="diagram-viewport">
    <img src="../assets/diagrams/analysis-workflow.svg" alt="Analysis workflow with admission, immutable input pinning, deterministic evidence branches, budget preflight, structured assessment, application validation, persistence, review and publication gates." />
  </div>
  <figcaption>02 · Execution path and the controls that prevent partial evidence, invalid model output or exhausted budgets from becoming false success.</figcaption>
</figure>

The important production invariants are:

1. **Durable acceptance.** Commit the job, idempotency record and durable dispatch intent before acknowledging. Reconcile workflow-start failures rather than leaving accepted jobs stranded.
2. **Pinned evidence.** Pin source versions, parser, pipeline and policy. A moving branch name is not immutable evidence.
3. **Visible completeness.** Each evidence branch reports success, failure and completeness. Required evidence that is missing or stale forces a bounded recovery path or an inconclusive result.
4. **Shared budget.** Retries, repairs and optional verification use the same cumulative cost/call allowances and end-to-end deadline.
5. **Validated persistence.** Validate evidence references, versions, applicability, contradictions and state transitions in Go before committing findings.
6. **Fresh publication.** Persist findings and provenance before publishing. Recheck source freshness and use separate idempotency for publication.

## OpenSpec-driven delivery

<figure class="diagram-figure">
  <div class="diagram-viewport">
    <img src="../assets/diagrams/engineering-loop.svg" alt="Engineering lifecycle from OpenSpec proposal and behavioral scenarios through failing tests, implementation, layered verification, adversarial review and archive." />
  </div>
  <figcaption>03 · Requirements and scenarios map to tests and evaluation evidence; archive follows verification, not just code completion.</figcaption>
</figure>

## Token and cost controls

<figure class="diagram-figure">
  <div class="diagram-viewport">
    <img src="../assets/diagrams/token-budget.svg" alt="Token-budget flow with request counting, deterministic compaction, reserved output budget, per-job spend and call ceilings, provider-usage reconciliation and stop conditions." />
  </div>
  <figcaption>04 · Input/output token limits alone are insufficient: spend, retries, concurrency and deadlines must also be bounded.</figcaption>
</figure>

## Authority by concern

| Concern | Authoritative owner | Explicit non-goal |
|---|---|---|
| Identity and tenant scope | Ingress and server-side authorization | The model never grants access |
| Async job lifecycle | Step Functions plus durable job/dispatch state | No competing agent graph as a second orchestrator |
| Domain policy | Pure Go functions over explicit, versioned inputs | No policy solely in prompts or workflow expressions |
| Model requests | Typed harness: budgets, versions, deadlines and retries | No unbounded context or tool loop |
| Provenance | Immutable artifact versions, stable locators and digest checks | Never silently fall back to latest source |
| Audit | Durable AuditEvent and ModelRun records | Traces are not the audit system of record |
| Quality | Unit/property/contract/integration tests plus labeled AI evaluations | A successful build is not behavioral proof |

## Further reading

- [Adversarial design review](ADVERSARIAL_DESIGN_REVIEW.md)
- [Engineering playbook](ENGINEERING_PLAYBOOK.md)
- [AI pipeline and token budgets](AI_PIPELINE.md)
- [Functional core / imperative shell](FUNCTIONAL_CORE.md)
- [Operations and recovery](OPERATIONS.md)
