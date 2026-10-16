## Selection and documentation
- [ ] Review the stack recommendation and approve/reject each recommended baseline item.
- [ ] Keep the provider direct to Anthropic; do not add model/provider SDKs absent an approved need.
- [ ] Record any adoption of Eino or another agent framework with a bounded use case and comparison to explicit Go orchestration.
- [ ] Keep memory source-of-truth and conversational-memory use cases separate.

## Harness and security
- [ ] Implement a narrow Go Anthropic adapter and operation-specific request/response types.
- [ ] Add bounded call/time/token budgets and error classification.
- [ ] Validate schema, evidence IDs, immutable source versions, applicability and allowed state transitions.
- [ ] Version prompts, schemas, model configuration and evaluation data.
- [ ] Implement prompt/cache behavior only after usage evidence and data-policy review.
- [ ] Add trace/log redaction checks and verify secrets/source excerpts are absent from default telemetry.

## Evaluation and observability
- [ ] Add Go unit/integration tests for deterministic policy and evidence checks.
- [ ] Create the initial labeled deviation/no-deviation/inconclusive/applicability corpus.
- [ ] Integrate Promptfoo or an equivalent approved evaluation runner and save result artifacts.
- [ ] Instrument ingress, retrieval, model calls, validation and persistence with OpenTelemetry.
- [ ] Add eval and tracing tests to CI for relevant changes.
- [ ] Select at most one hosted trace/eval product after privacy, cost and operation review.

## Adoption gates
- [ ] Measure retrieval recall/precision before adopting embeddings/reranking.
- [ ] Benchmark Eino against explicit Go functions before adding it.
- [ ] Defer memory products, MCP and multi-agent loops until a concrete consumer/requirement exists.
- [ ] Set quality thresholds from measured pilot results rather than invented initial numbers.
