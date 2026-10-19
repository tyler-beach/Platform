const e=`# Project brief

## Purpose
The ADR Deviation Platform detects and explains inconsistencies between architectural decision records (ADRs), plain-English technical specifications, and implementation changes. It is an engineering decision-support service, not a replacement for architecture governance and not an autonomous code-changing agent.

## Core comparison modes
1. **Implementation ↔ ADR:** does a code change or observed implementation conflict with an applicable, accepted decision?
2. **Specification ↔ ADR:** does a technical specification conflict with, violate, or omit an applicable architecture constraint?
3. **Specification ↔ implementation:** does the implementation satisfy the documented requirements?

Code changes and specification documents are both first-class inputs; analysis must not assume every job starts from a pull request.

## Goals
- Produce traceable findings, with source artifact versions and precise evidence locations.
- Establish decision applicability using status, scope, service/repository relationships, ownership, time and supersession.
- Prefer deterministic evidence collection and checks; use AI for bounded semantic interpretation.
- Return typed outcomes, uncertainty and missing-evidence states.
- Make jobs retryable, idempotent, observable and bounded in cost.
- Enable human review and learn from dispositions without automatically changing authoritative decisions.
- Keep the primary application language Go.

## Non-goals for the initial release
- Automatically changing code, ADRs or production infrastructure.
- A general autonomous multi-agent platform.
- Conversational memory as the source of institutional decision knowledge.
- A separate graph database before query evidence warrants it.
- Supporting every programming language and document format immediately.
- Blocking pull requests from unvalidated model output.
- Creating Lambda functions dynamically at runtime.

## Principles
1. Evidence before explanation.
2. Applicability before contradiction.
3. Deterministic first, AI where it adds value.
4. Explicit types and versioned contracts.
5. Source documents remain authoritative; indexes and summaries are derived.
6. Missing/stale evidence means unknown, not an invented conclusion.
7. Humans retain decision authority.
8. Keep stages small, testable and independently observable.
9. Security applies to source content, model input, output and every integration.
10. Build one end-to-end vertical slice before adding more frameworks.

## Initial acceptance target
Accept a code change and a known ADR; resolve relevant evidence; call Anthropic for a structured assessment; verify every cited reference; persist a result; and explain the result to a reviewer. Include a true deviation, a similar non-deviation, an irrelevant ADR, and an insufficient-evidence case.

## Status language
This repository is a **design baseline**, not evidence that any service or cloud infrastructure is deployed. Recommendations are not accepted architecture decisions until explicitly reviewed and recorded. Use docs/DECISIONS.md and docs/OPEN_QUESTIONS.md to track that distinction.
`;export{e as default};
