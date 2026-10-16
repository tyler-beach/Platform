# Change: select AI runtime and tooling baseline

## Why
The platform needs an explicit, Go-compatible selection for the non-model parts of an AI system: SDK/harness, orchestration boundaries, memory/context, evaluations, tracing, prompt management, and optional tool protocols. Without a selection, a coding agent may install overlapping frameworks or a memory store that does not fit the source-of-truth problem.

## Proposed change
Document and adopt a lean default around the official Anthropic Go SDK and a custom typed harness; Step Functions remains the distributed workflow owner. Use OpenTelemetry for instrumentation, Go tests plus Promptfoo for AI behavior regression, and Postgres-backed versioned knowledge/retrieval. Treat CloudWeGo Eino as the first Go-native AI graph candidate only if model-internal orchestration becomes necessary. Defer memory products and hosted eval/tracing vendors pending a pilot and data review.

## Scope
- Publish a technology-selection matrix with adopt/defer/conditional choices.
- Define harness boundaries, validation, prompt/schema versioning and spend controls.
- Distinguish execution state, architectural knowledge, retrieval index, prompt cache and conversational memory.
- Define evaluation/trace requirements and privacy defaults.
- Add an OpenSpec spec and tasks to keep future AI tooling changes evidence-based.

## Non-goals
- Add AI dependencies to go.mod or deploy any hosted observability product.
- Implement the actual harness, retriever, memory system, evaluator or workflow.
- Change the confirmed direct Anthropic provider preference.
- Replace Step Functions with an agent framework.
- Force LangGraph, Eino, LangChainGo, Mem0, Zep, Braintrust, Langfuse or MCP into the MVP.

## Acceptance criteria
- The recommended baseline is explicit and separated from conditional options.
- Every optional framework/tool has a concrete threshold for adoption.
- Memory guidance distinguishes authoritative architecture records from conversational memory.
- Evaluation, tracing and redaction requirements are testable.
- OpenSpec makes unapproved dependencies, unbounded agent loops and source-data leakage disallowed.
- Documentation states that no tests/deployments were run as part of this design-only change.
