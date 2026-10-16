<div class="platform-hero" markdown>
<span class="platform-eyebrow">EVIDENCE-FIRST · VERSIONED · REVIEWABLE</span>

# ADR Deviation Platform

Compare architectural decisions, technical specifications, and implementation changes—with traceable evidence and reviewable explanations when they diverge.

<div class="platform-hero-actions" markdown>
[Get started](getting-started.md){ .md-button .md-button--primary }
[Explore architecture](architecture.md){ .md-button }
[Engineering playbook](ENGINEERING_PLAYBOOK.md){ .md-button }
[API reference](api/index.md){ .md-button }
</div>
</div>

## Explore the platform

<div class="grid cards" markdown>

-   :material-graph-outline: **Architecture and workflows**

    ---

    Detailed reference architecture, analysis lifecycle, token-budget gates and deployment profiles.

    [:octicons-arrow-right-24: Explore diagrams](architecture.md)

-   :material-api: **API reference**

    ---

    Explore the proposed OpenAPI contract in Swagger UI. The API is a design contract, not a deployed service.

    [:octicons-arrow-right-24: Explore API](api/index.md)

-   :material-database-check: **Data contracts**

    ---

    Understand invariants for artifacts, jobs, findings, evidence, reviews and audit records.

    [:octicons-arrow-right-24: Read contracts](contracts/CONTRACTS.md)

-   :material-file-document-check: **Evidence and provenance**

    ---

    See how findings tie back to exact, immutable source versions and locations.

    [:octicons-arrow-right-24: Evidence rules](contracts/EVIDENCE.md)

-   :material-test-tube: **Engineering playbook**

    ---

    OpenSpec-driven behavior design, functional core practices, red-green-refactor and test traceability.

    [:octicons-arrow-right-24: Start engineering](ENGINEERING_PLAYBOOK.md)

-   :material-shield-check: **Adversarial design review**

    ---

    Distributed reliability, token economics, trust boundaries and unresolved production decisions.

    [:octicons-arrow-right-24: Review the risks](ADVERSARIAL_DESIGN_REVIEW.md)

</div>

## Core comparison modes

~~~mermaid
flowchart LR
  ADR[Architectural decisions] --> IA[Implementation ↔ ADR]
  SPEC[Technical specification] --> SA[Specification ↔ ADR]
  SPEC --> SI[Specification ↔ implementation]
  CODE[Code change / source snapshot] --> IA
  CODE --> SI
  IA --> E[Versioned evidence package]
  SA --> E
  SI --> E
  E --> V[Deterministic validation]
  V --> A[Bounded structured assessment]
  A --> R[Validated finding]
  R --> H[Human review when required]
~~~

## Design status

This repository is an architecture and contract baseline. The production API, generated service code, state-machine implementation, persistence layer and model harness are not yet claimed to exist. The diagrams describe intended boundaries and controls, not deployed resources.

**No finding without evidence, no constraint without applicability, and no model output without application validation.**

## Start here

- [Getting started](getting-started.md)
- [System architecture and detailed workflows](architecture.md)
- [OpenSpec and test-driven engineering](ENGINEERING_PLAYBOOK.md)
- [Adversarial design review](ADVERSARIAL_DESIGN_REVIEW.md)
- [API reference](api/index.md)
- [Data contracts](contracts/CONTRACTS.md)
- [Logging and audit](contracts/LOGGING_AND_AUDIT.md)
- [Repository README](https://github.com/tyler-beach/Platform/blob/main/README.md)
