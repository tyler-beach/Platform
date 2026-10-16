# AI / LLM technology selection

**Reviewed:** 2026-10-16  
**Status:** Recommended baseline, subject to evaluation and explicit approval where noted.

This document selects the technology surrounding Anthropic for the ADR Deviation Platform. "Industry standard" here means an established protocol, official SDK, or broadly usable engineering practice—not a claim that one commercial framework is universally standard.

## Executive recommendation

Build an **evidence-first Go harness around the official Anthropic Go SDK**. Keep top-level asynchronous workflow in AWS Step Functions. Use first-party schema-constrained model output plus application-level evidence/policy validation. Use PostgreSQL as the authoritative knowledge store, OpenTelemetry as the instrumentation standard, and a language-independent evaluation runner such as Promptfoo for prompt/e2e regression tests. Do not adopt a dedicated memory product or agent framework for the first vertical slice.

### Adopt now / make part of the baseline

| Capability | Recommendation | Reason |
|---|---|---|
| Anthropic API | Official github.com/anthropics/anthropic-sdk-go | First-party typed API client; direct Anthropic API is the confirmed provider choice. |
| Harness | Small custom Go package over the official SDK | The platform needs explicit budgets, provenance and validation more than generic agent abstractions. |
| Structured output | Anthropic schema-constrained JSON output / strict tool schema when supported | Machine-readable response shape; still validate meaning and evidence in Go. |
| Workflow | AWS Step Functions for distributed job lifecycle; explicit Go functions inside individual workers | Durable stage/retry/branch behavior outside the LLM loop; no competing workflow owners. |
| Prompt management | Versioned prompt files in Git, tied to schema, pipeline, model and evaluation versions | Reviewable diffs, normal CI and rollback without adding another service. |
| Runtime telemetry | OpenTelemetry Go, using current GenAI semantic conventions where they fit | Vendor-neutral traces, metrics and logs across API, workflow, workers, DB and model calls. |
| Evaluation | Go unit/integration tests plus a small Promptfoo evaluation suite in CI | Deterministic invariants and model behavior are tested separately; works regardless of app language. |
| Knowledge store | PostgreSQL + explicit relationships + full-text search; pgvector only after retrieval evaluation | Architectural decisions are source-of-truth domain data, not conversational memory. |
| Guardrails | Domain validation in Go, supported by schema checks and explicit policy/rules | Key protections are evidence-reference checks, applicability, authorization and allowed state transitions—not a generic text filter. |

## The Go harness

Build a narrow adapter at internal/ai/anthropic with a stable domain interface. It should support named operations such as requirement extraction, ADR interpretation, applicability assessment, deviation assessment and selective verification.

The harness owns:
- model configuration and explicit operation allowlists;
- request construction and versioned prompt/schema selection;
- evidence-package and token/cost budgets;
- timeout/deadline propagation, retry classification and cancellation;
- Anthropic response parsing and response metadata;
- schema checks plus semantic validation of evidence IDs and source versions;
- token usage, latency, provider request IDs and outcome recording;
- bounded repair handling (at most one controlled retry where useful);
- prompt-cache configuration for repeated stable prefixes when applicable.

Do not let every application package construct raw model requests independently. Do not treat a valid JSON response as a valid finding.

### Structured output vs tool use

For a job such as "compare these evidence items to this ADR and return findings", prefer structured output as the main result contract. Use tool calls only when the model needs to request a narrowly defined read operation that cannot be completed deterministically in advance.

If tool use is added:
- the application executes tools; the model only proposes tool calls;
- expose only read-only, allowlisted tools for analysis by default;
- validate arguments and authorization in Go;
- enforce maximum tool calls, total wall-clock time and total tokens;
- never expose shell, arbitrary Git writes, AWS mutations, credentials or unrestricted repository access;
- record each request/result in the job trace and evidence ledger.

The official SDK includes tool-runner helpers, but an automatic conversation/tool loop can obscure control flow. Prefer an explicit bounded loop for this platform until there is a specific reason to adopt the helper. Official references: [Anthropic Go SDK](https://github.com/anthropics/anthropic-sdk-go), [Go SDK tool helpers](https://github.com/anthropics/anthropic-sdk-go/blob/main/tools.md), [Anthropic tool-use contract](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works), and [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).

### Prompt caching

Consider Anthropic prompt caching after measuring repeated prefixes such as stable system instructions, tool schemas or standard evaluation examples. Keep stable instructions before per-job evidence, and record cache-read/write usage where provided. Cache only content permitted by data-handling policy; caching is an efficiency feature, not durable memory. Official guide: https://platform.claude.com/docs/en/build-with-claude/prompt-caching.

Do not optimize around cache hits before usage traces show repeated prefix cost is material.

## LLM orchestration: what to use and when

Two independent levels must remain separate:

1. **Application workflow orchestration** — AWS Step Functions owns job state, Lambda invocation, deadlines, retries, parallel branches, and human-review waits.
2. **LLM reasoning orchestration** — only needed if a model task genuinely requires a conditional graph, bounded tool loop, checkpoint/resume, or multi-stage agent state.

| Option | Fit for this Go-first platform | Recommendation |
|---|---|---|
| Explicit Go functions + state machine | Predictable bounded stages; easy to inspect, test and control | **Start here.** |
| [CloudWeGo Eino](https://www.cloudwego.io/docs/eino/overview/) | Go-native chains, graphs, workflows, agents and interruption/resumption; Claude integration exists in eino-ext | **First candidate to evaluate** if complex AI-level orchestration becomes necessary. Evaluate dependency footprint and API stability before adopting. |
| [LangChainGo](https://github.com/tmc/langchaingo) | Community Go composition/agent library | Alternative if its specific components save measured work; not needed just to call an LLM. |
| [LangGraph](https://github.com/langchain-ai/langgraphjs) | Stateful graph orchestration with durable execution and human-in-the-loop in its Python/JS ecosystem | Prefer only if the team explicitly accepts a separate Python/JS subservice. Do not add a second language just to use a framework. |
| Multiple autonomous agents / supervisor pattern | Multiple independent reasoning roles and control loops | Defer; every extra agent increases cost, latency and evaluation surface. |

Eino is a credible option rather than an automatic choice: its official documentation describes typed Go workflows/graphs and agent capabilities, and its extension repository includes a Claude model implementation. Keep it as an evaluated option, not a dependency until the first vertical slice demonstrates a need. References: https://www.cloudwego.io/docs/eino/overview/ and https://github.com/cloudwego/eino-ext/tree/main/components/model/claude.

**Never make Step Functions and an agent graph both the authority for the same overall job lifecycle.** A future Eino graph, if adopted, should be a bounded sub-workflow invoked by one Step Functions task.

## Memory and context: use the right kind

The platform does not primarily need an agent to remember past conversations. It needs trustworthy, versioned architectural knowledge.

| Kind of context/state | Store / mechanism | Guidance |
|---|---|---|
| Job execution state and retry state | Step Functions + job row in PostgreSQL | Durable operation state, not LLM memory. |
| ADRs/specs/code and their history | Source system + immutable artifact/version records; S3 for large snapshots as needed | Authoritative inputs and audit provenance. |
| Decision scope, supersession, service ownership and dependency relationships | Relational relationship tables initially | Explicit queryable facts with provenance; use a graph database only if query/scale evidence demands it. |
| Relevant passages | PostgreSQL full-text + structured metadata, symbol/identifier lookups | First retrieval layer. |
| Semantic candidate retrieval | pgvector in PostgreSQL, if measured necessary | Supplement exact/lexical retrieval; do not infer policy applicability from similarity alone. |
| Model prompt prefix cache | Anthropic prompt caching | Temporary compute/cost optimization, not persistent knowledge. |
| Cross-conversation/user personalization | Dedicated memory products such as Mem0 or Zep | Not required for this service's core domain. Reassess only if a separate use case emerges. |

For retrieval, preserve this order: exact IDs and explicit relationships → status/scope metadata filters → identifiers/symbols/paths → full-text search → semantic vector candidates → optional reranking if evaluation justifies it. Every returned item carries a stable evidence ID tied to an immutable source version.

A dedicated memory framework can be useful for assistant products that remember a person's conversation/history. It is not a substitute for decision lifecycle, versioning, permissions, supersession and evidence provenance. Zep, for example, describes memory around user/thread context and offers a Go client, but that is a different problem from authoritative architecture governance: https://help.getzep.com/v4/quick-start-guide and https://github.com/getzep/zep-go.

## Retrieval, embedding and reranking

Do not select an embedding/reranking provider as a default before building a labeled retrieval set. Start with:
1. exact lookup by ADR/requirement ID and explicit relationship;
2. scope and lifecycle filters;
3. path/symbol/API/config identifiers;
4. PostgreSQL full-text search;
5. pgvector semantic retrieval if missed relevant decisions remain.

Measure recall@k and precision@k for the applicable governing decision. Only then test embedding models or rerankers. Pin model/version and index version in every retrieval record. Never allow vector similarity to override accepted/rejected/superseded status or authorization.

Reference: [pgvector hybrid search](https://github.com/pgvector/pgvector).

## Evaluation and LLM observability

Use different tools for different jobs:

- **Required baseline:** Go unit/integration tests and versioned labeled cases for deviation/no-deviation/applicability/evidence correctness.
- **Prompt/e2e evaluation:** [Promptfoo](https://www.promptfoo.dev/docs/guides/) CLI/provider configuration for the Anthropic model, prompt regression, structured-output checks, and selected model-graded cases. Because it runs independently of the Go runtime, the service need not adopt a JavaScript framework.
- **Production traces:** [OpenTelemetry Go](https://opentelemetry.io/docs/languages/go/) as the instrumented interface. Trace ingress → Step Functions/job stages → retrieval → model call → validation → persistence. Adopt applicable [GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) while accounting for their current evolution.
- **Optional hosted experiment platform:** [Braintrust Go SDK](https://github.com/braintrustdata/braintrust-sdk-go) is a possible integrated option for Go tracing and evals, but its repository currently labels the SDK beta. Evaluate its API stability, hosting/data policy and cost before adoption.
- **Optional tracing backend:** a Langfuse or other OpenTelemetry-compatible backend may be selected later. Keep instrumentation vendor-neutral until hosting, privacy and operational needs are known.

Do not adopt Promptfoo, Braintrust and Langfuse simultaneously at the outset. My proposed default is **Promptfoo for repeatable prompt/e2e evals + OpenTelemetry for traces**, then choose one hosted observability/evaluation backend only if the pilot needs datasets, experiment comparisons or a reviewer UI.

References: https://www.promptfoo.dev/docs/providers/anthropic/ ; https://www.promptfoo.dev/docs/guides/ ; https://github.com/braintrustdata/braintrust-sdk-go ; https://langfuse.com/docs/observability/sdk/overview.

## Prompt and model management

Store prompts in Git by operation, with a stable ID/version and paired schema. Each result should record:
- provider and returned model ID (plus configured alias);
- prompt file/version/hash and schema version/hash;
- operation name and relevant generation parameters;
- source artifact/version IDs and evidence IDs supplied;
- response/request ID, token usage, latency, retry count and validation outcome;
- evaluation corpus/version used for release comparison.

Choose model tiers by evaluation and cost, not model-name prestige. Keep model aliases/configuration out of domain logic. Run the same labeled dataset when changing model, prompt, parser, retriever, schema or finding policy. Human-review a sample of regressions before rollout.

## Guardrails / policy enforcement

Use deterministic controls in Go:
- validate structured schema and field bounds;
- validate each cited evidence ID exists in the job package;
- verify exact source version, decision status and applicability;
- reject unauthorized repositories/workspaces and stale versions;
- separate outcome, severity, quality/confidence and review state;
- require explicit review for policy-selected ambiguous/high-impact findings;
- prevent model output from invoking unapproved actions or changing workflow state;
- retain an audit record of validation failures.

A dedicated "LLM guardrails" framework is not required to implement these controls. Add a policy engine such as OPA/Cedar only if rules must be managed centrally across services or by non-developers. Keep policy deterministic and independently testable.

## MCP and API protocols

The platform already has a proposed gRPC/Protobuf control-plane contract. **MCP is not a replacement for that API or for Step Functions.** Consider [MCP Go](https://github.com/mark3labs/mcp-go) only if Claude Code or another compatible LLM client should discover/call a bounded set of platform tools such as get_finding or search_applicable_adrs. Start read-only; authenticate and authorize every request. Do not expose unrestricted source, filesystem, Git write or AWS tools just because an MCP interface exists.

## What not to install by default

- LangGraph/agent frameworks before the first vertical slice.
- An agent memory platform for ADR/specification provenance.
- A separate vector database when PostgreSQL can meet early needs.
- An LLM gateway/proxy solely for one configured provider.
- Multiple tracing/evaluation products that overlap.
- A generic guardrail package instead of explicit policy checks.
- Embeddings/reranking before establishing a retrieval benchmark.
- An open-ended agent/tool loop for a task that can be solved with one structured assessment.

## Recommended order of adoption

1. Official Anthropic Go SDK + a small typed harness.
2. Go validation and deterministic evidence assembly.
3. Unit/integration tests + versioned evaluation cases; Promptfoo for prompt/e2e regression.
4. OpenTelemetry tracing/metrics, with redaction and retention controls.
5. Postgres metadata/full-text relationships; pgvector after retrieval evaluation.
6. CloudWeGo Eino only if an AI-internal graph/tool orchestration need is demonstrated.
7. One hosted observability/evaluation platform only if the team needs its dataset, review or experiment UI.
8. MCP server only when there is an identified client integration need.
