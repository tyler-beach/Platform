# ADR Deviation Platform

An evidence-first platform for detecting inconsistencies between architectural decisions, technical specifications, and implementation changes.

This is the living design notebook and engineering baseline. It separates confirmed direction, recommended defaults, and open questions. Proposed choices are not accepted architecture decisions until explicitly reviewed.

## Documentation site

The documentation source is in the docs folder and is built with MkDocs Material. After the first successful GitHub Pages deployment, the site should be available at:

**https://tyler-beach.github.io/Platform/**

- [Interactive API / Swagger UI](https://tyler-beach.github.io/Platform/api/)
- [Data contracts](https://tyler-beach.github.io/Platform/contracts/CONTRACTS/)
- [Evidence contract](https://tyler-beach.github.io/Platform/contracts/EVIDENCE/)
- [Logging and audit contract](https://tyler-beach.github.io/Platform/contracts/LOGGING_AND_AUDIT/)
- [Architecture diagrams](https://tyler-beach.github.io/Platform/architecture/)

The Pages URL is expected but will not be live until GitHub Actions deploys the site and repository Pages settings allow workflow-based deployment. The REST/OpenAPI document is a proposed façade, not a claim of a deployed HTTP server.

## Start here in the repository

- [Project brief](docs/PROJECT_BRIEF.md)
- [Architecture overview](docs/ARCHITECTURE.md)
- [gRPC and Protobuf design](docs/RPC_AND_PROTOBUF.md)
- [AI pipeline and harness](docs/AI_PIPELINE.md)
- [Go tooling](docs/GO_TOOLING.md)
- [Data model](docs/DATA_MODEL.md)
- [Operations and reliability](docs/OPERATIONS.md)
- [OpenSpec workflow and guardrails](docs/OPEN_SPEC_WORKFLOW.md)
- [Security](docs/SECURITY.md)
- [Evaluation](docs/EVALUATION.md)
- [Roadmap](docs/ROADMAP.md)
- [Decision log](docs/DECISIONS.md)
- [Open questions](docs/OPEN_QUESTIONS.md)
- [Architecture diagrams](docs/diagrams/architecture.md)
- [Protobuf contract](proto/adrplatform/v1/platform.proto)

## Current direction at a glance

- **Language:** Go for the application, deterministic analysis, gRPC API, and workers.
- **AI provider:** Anthropic API directly, not Amazon Bedrock.
- **Workflow:** AWS Step Functions is the recommended top-level owner for async analysis; it invokes reusable Lambda workers.
- **RPC/contracts:** Protobuf contract-first API; gRPC for synchronous job-control calls if a long-lived API is justified. Do not host a gRPC listener in ordinary Lambda workers.
- **Runtime options:** a webhook/serverless profile may use HTTP/API Gateway + Lambda; a true gRPC endpoint needs a long-lived service such as ECS/Fargate behind an HTTPS ALB.
- **Data:** PostgreSQL/Aurora; pgvector is optional and should be justified by retrieval evaluations. S3 for large or immutable artifacts as needed.
- **Reasoning:** deterministic evidence collection, bounded structured model assessment, application validation, selective independent verification.
- **Development:** OpenSpec for behavior changes, review, implementation, test/evaluation and archive.
- **Deferred:** autonomous multi-agent loops, dedicated conversational memory, separate graph database, A2A and automatic remediation.

These are recommendations, not proof that infrastructure exists. The gRPC API hosting choice and several product/runtime details remain open.

## API, contracts, evidence, and website

- [Proposed REST/OpenAPI contract](docs/openapi.yaml)
- [API semantics and versioning](docs/contracts/API_CONTRACT.md)
- [Domain data contracts](docs/contracts/CONTRACTS.md)
- [Evidence and provenance contract](docs/contracts/EVIDENCE.md)
- [Logging, tracing, metrics, and audit contract](docs/contracts/LOGGING_AND_AUDIT.md)
- [MkDocs site configuration](mkdocs.yml)
- [Documentation build/deploy workflow](.github/workflows/docs.yml)

## AI / LLM tooling and functional design

- [AI technology selection](docs/AI_TECHNOLOGY_SELECTION.md)
- [AI technology decision matrix](docs/AI_TECHNOLOGY_DECISION_MATRIX.md)
- [AI evaluation and observability](docs/AI_EVALUATION_OBSERVABILITY.md)
- [Functional core / imperative shell review](docs/FUNCTIONAL_CORE.md)

Current recommendation: official Anthropic Go SDK behind a small typed harness; Step Functions for distributed workflows; OpenTelemetry for traces; Promptfoo plus Go tests for AI regression; PostgreSQL for versioned architecture knowledge. Use functional-core/imperative-shell: pure Go domain transforms and explicit effect boundaries. Agent frameworks, conversational-memory services and hosted observability products remain conditional.

## Core comparisons

1. **Implementation ↔ ADR:** does a change or code behavior conflict with an applicable accepted decision?
2. **Specification ↔ ADR:** does a technical spec conflict with or omit an architecture constraint?
3. **Specification ↔ implementation:** does implementation behavior satisfy documented intent?

Code changes and plain-English technical specifications are both first-class inputs. Findings must be evidence-backed and distinguish supported deviation, potential deviation, no deviation found, and inconclusive.

## Status

Design baseline / planning repository. Protobuf schema and Buf configuration are design artifacts; this repository does not yet contain the production gRPC server, generated Go code, deployed infrastructure, or a validated end-to-end pipeline. OpenSpec validation, Protobuf lint/build, OpenAPI lint and the MkDocs site build still need to be run after these documentation changes.

## Guiding rule

> No finding without evidence; no architectural constraint without applicability; no model output without validation.
