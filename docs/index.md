# ADR Deviation Platform

An evidence-first platform to compare architectural decisions, technical specifications, and implementation changes—and give engineers a traceable, reviewable explanation when they diverge.

<div class="grid cards" markdown>

-   :material-api: **API reference**

    ---

    Browse the first-pass OpenAPI contract in interactive Swagger UI.

    [:octicons-arrow-right-24: Explore API](api/index.md)

-   :material-database-check: **Data contracts**

    ---

    Understand artifact versions, jobs, findings, evidence, review and audit invariants.

    [:octicons-arrow-right-24: Read contracts](contracts/CONTRACTS.md)

-   :material-file-document-check: **Evidence and provenance**

    ---

    How every finding must resolve to exact source versions and locations.

    [:octicons-arrow-right-24: Evidence rules](contracts/EVIDENCE.md)

-   :material-route: **Architecture**

    ---

    See the system context, asynchronous pipeline and trust boundaries.

    [:octicons-arrow-right-24: View architecture](architecture.md)

-   :material-school: **How-to guides**

    ---

    Learn how to add an input source, a comparison mode, or a Go worker safely.

    [:octicons-arrow-right-24: Start building](how-to/index.md)

-   :material-monitor-dashboard: **Operations**

    ---

    Logging, tracing, failure behavior, idempotency and reliability guidance.

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

This repository is the architecture and contract baseline. The API implementation, generated code, workflow, persistence layer and production service are not yet claimed to exist. Published docs evolve with reviewed OpenSpec changes and schema versions.

**No finding without evidence, no constraint without applicability, and no model output without application validation.**

## Start here

- [Getting started](getting-started.md)
- [Architecture and diagrams](architecture.md)
- [API reference](api/index.md)
- [Data contracts](contracts/CONTRACTS.md)
- [Logging and audit](contracts/LOGGING_AND_AUDIT.md)
- [How-to guides](how-to/index.md)
- [Repository README](https://github.com/tyler-beach/Platform/blob/main/README.md)
