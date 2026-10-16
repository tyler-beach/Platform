<div class="platform-hero" markdown>
<span class="platform-eyebrow">EVIDENCE-FIRST · VERSIONED · REVIEWABLE</span>

# ADR Deviation Platform

Compare architectural decisions, technical specifications, and implementation changes—with traceable evidence and reviewable explanations when they diverge.

<div class="platform-hero-actions" markdown>
[Get started](getting-started.md){ .md-button .md-button--primary }
[Explore architecture](architecture.md){ .md-button }
[API reference](api/index.md){ .md-button }
</div>
</div>

## Explore the platform

<div class="grid cards" markdown>

-   :material-api: **API reference**

    ---

    Explore the proposed OpenAPI contract in the interactive Swagger UI.

    [:octicons-arrow-right-24: Explore API](api/index.md)

-   :material-database-check: **Data contracts**

    ---

    Understand the invariants for artifacts, jobs, findings, evidence, reviews, and audit records.

    [:octicons-arrow-right-24: Read contracts](contracts/CONTRACTS.md)

-   :material-file-document-check: **Evidence and provenance**

    ---

    See how findings tie back to exact, immutable source versions and locations.

    [:octicons-arrow-right-24: Evidence rules](contracts/EVIDENCE.md)

-   :material-route: **Architecture**

    ---

    Follow the system context, asynchronous workflow, and trust boundaries.

    [:octicons-arrow-right-24: View architecture](architecture.md)

-   :material-school: **How-to guides**

    ---

    Learn how to add an input source, comparison mode, or Go worker safely.

    [:octicons-arrow-right-24: Start building](how-to/index.md)

-   :material-monitor-dashboard: **Operations**

    ---

    Review logging, tracing, failure handling, idempotency, and reliability guidance.

    [:octicons-arrow-right-24: Operational contracts](contracts/LOGGING_AND_AUDIT.md)

</div>

## Core comparisons

~~~mermaid
flowchart LR
  ADR[Architectural Decisions] --> IA[Implementation ↔ ADR]
  SPEC[Technical Specification] --> SA[Specification ↔ ADR]
  SPEC --> SI[Specification ↔ Implementation]
  CODE[Code Change / Source Snapshot] --> IA
  CODE --> SI
  IA --> E[Versioned Evidence Package]
  SA --> E
  SI --> E
  E --> V[Deterministic Validation]
  V --> A[Bounded Structured Assessment]
  A --> R[Validated Finding]
  R --> H[Human Review when required]
~~~

## Design status

This repository is the architecture and contract baseline. The API implementation, generated code, workflow, persistence layer, and production service are not yet claimed to exist. Published docs evolve with reviewed OpenSpec changes and schema versions.

**No finding without evidence, no constraint without applicability, and no model output without application validation.**

## Start here

- [Getting started](getting-started.md)
- [Architecture and diagrams](architecture.md)
- [API reference](api/index.md)
- [Data contracts](contracts/CONTRACTS.md)
- [Logging and audit](contracts/LOGGING_AND_AUDIT.md)
- [How-to guides](how-to/index.md)
- [Repository README](https://github.com/tyler-beach/Platform/blob/main/README.md)
