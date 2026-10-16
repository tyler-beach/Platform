# ADR Deviation Platform

An evidence-first platform for detecting inconsistencies between architectural decisions, technical specifications, and implementation changes.

This repository is the living design notebook and engineering baseline for the platform. It intentionally separates **decisions discussed so far**, **recommended defaults**, and **open questions**. Proposed choices are not treated as irrevocable architecture decisions until recorded as accepted ADRs.

## Start here

- [Project brief and scope](docs/PROJECT_BRIEF.md)
- [Architecture overview](docs/ARCHITECTURE.md)
- [AI pipeline and harness](docs/AI_PIPELINE.md)
- [Go-first implementation guidance](docs/GO_TOOLING.md)
- [OpenSpec workflow and guardrails](docs/OPENSPEC_WORKFLOW.md)
- [Security and trust boundaries](docs/SECURITY.md)
- [Evaluation strategy](docs/EVALUATION.md)
- [Implementation roadmap](docs/ROADMAP.md)
- [Decision log](docs/DECISIONS.md)
- [Known open questions](docs/OPEN_QUESTIONS.md)
- [Architecture diagrams](docs/diagrams/README.md)
- [OpenSpec current-state requirements](openspec/specs/README.md)

## Current direction at a glance

- **Primary language:** Go for the application, deterministic analysis, API, and workers.
- **AI provider:** Anthropic API directly (not Amazon Bedrock).
- **Top-level orchestration:** AWS Step Functions coordinating reusable Lambda workers is the current recommended default.
- **Data:** PostgreSQL/Aurora PostgreSQL; pgvector is optional and justified by measured semantic-retrieval needs.
- **Object/evidence storage:** S3 for immutable or large source snapshots and artifacts where required.
- **Reasoning style:** deterministic-first, evidence-grounded, schema-constrained AI calls, bounded retries/budgets, selective independent verification.
- **Development workflow:** OpenSpec for proposed behavioral changes, specs, design, tasks, review, implementation, verification, and archive.
- **Not required initially:** multi-agent autonomy, dedicated conversational memory, a separate graph database, A2A, or LangGraph.

These are working recommendations derived from design discussions, not proof that infrastructure has been deployed or code exists. See the decision log and open questions for the confidence/status of each item.

## Core problem

Detect and explain potential deviations across:

1. **Implementation ↔ ADR** — does a code change or codebase behavior violate an applicable accepted decision?
2. **Specification ↔ ADR** — does a technical specification conflict with, bypass, or omit a relevant architectural constraint?
3. **Specification ↔ implementation** — does the implementation match the documented intent and required behaviors?

Inputs may start from either code changes or plain-English technical specification documents. Results must be traceable to source artifacts and should distinguish confirmed conflicts, potential deviations, missing evidence, and no-deviation assessments.

## Status

Design baseline / planning repository. This commit captures the architecture discussed to date and gives future work an OpenSpec starting point. It is not a claim that the service has been implemented, deployed, or production validated.

## Guiding rule

> No finding without evidence; no architectural constraint without applicability; no model output without validation.

