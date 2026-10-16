# Design: AI runtime and tooling baseline

## Decision principle
A small harness should own the behavior specific to the product: evidence packaging, prompt/schema versioning, model-call budgets, finding validation and audit metadata. Reuse standards for transport/telemetry and managed orchestration where they materially reduce custom reliability work. Avoid an orchestration/memory/observability framework just because it appears in an AI stack diagram.

## Recommended default
- Direct model API via official Anthropic Go SDK.
- Custom, typed, bounded Go harness.
- Anthropic structured output/tool schemas, plus Go validation.
- Step Functions for distributed workflow and non-LLM Lambda tasks.
- PostgreSQL/versioned artifacts/relationships, full-text retrieval; pgvector only after retrieval benchmarks.
- Prompts stored/versioned in Git; native Anthropic prompt caching only for measured repeated prefixes.
- Go tests + labeled corpus + Promptfoo for prompt/e2e eval; OpenTelemetry for runtime traces/metrics.
- Hosted observability backend selected later based on privacy, self-hosting, costs and operational needs.

## Conditional Go graph framework
If the evidence assessment grows into conditional LLM sub-workflows with meaningful checkpointing, branch state or tool routing, evaluate CloudWeGo Eino first because it is Go-native and exposes chains/graphs/workflows and Claude integration. Compare its dependency tree, release cadence, observability hooks, schema/tool control and tests against an explicit Go state machine. Adopt only if the framework materially reduces complexity. LangGraph is a viable Python/JS option but not a reason by itself to add a second language.

## Memory design
- Job state/retries: Step Functions + PostgreSQL.
- Authoritative architecture/spec/code facts: source systems and artifact version records.
- Relationships: PostgreSQL edge/relationship tables.
- Retrieval: exact IDs/metadata/symbols/full-text first; vectors optional.
- Prompt caching: provider compute optimization.
- Conversational memory products: out of initial scope.

## Tool selection
Promptfoo provides a language-independent runner for Anthropic prompt/e2e evaluations. Go unit/integration tests remain the authority for hard domain invariants. OpenTelemetry provides vendor-neutral runtime instrumentation; select at most one hosted evaluation/trace backend after data-governance review. Braintrust Go SDK features are promising but beta, so production adoption needs an explicit API maturity review. Langfuse can ingest OpenTelemetry, but product selection remains open.

MCP is a future external tool interface only if an LLM client needs to discover/call approved platform operations. It is not the internal service API, not a replacement for gRPC/Protobuf, and not the workflow orchestrator.

## Data handling
Standard traces exclude raw source, prompt/response text and secrets. Store evidence references/hashes, counts, versions, token use, latency and validation result. Payload capture, if ever necessary, is opt-in, redacted, restricted and retention-limited.
