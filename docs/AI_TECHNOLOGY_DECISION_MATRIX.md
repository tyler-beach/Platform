# AI technology decision matrix

This is the concise approval checklist for the detailed recommendations in [AI technology selection](AI_TECHNOLOGY_SELECTION.md).

| Technology/capability | Proposed status | Adopt when |
|---|---|---|
| official Anthropic Go SDK | Baseline | First model call |
| custom Go harness | Baseline | First model call; always retain application validation |
| Anthropic structured output/tool schemas | Baseline where supported | Every typed assessment |
| Step Functions | Baseline for distributed async workflow | Multi-stage Lambda workflow |
| OpenTelemetry Go | Baseline | Add traces around API, stages, retrieval, provider and validation |
| Go unit/integration tests | Baseline | Every PR |
| Promptfoo | Recommended eval runner | When first labeled prompt/assessment cases exist |
| Prompt files in Git | Baseline | Before first model prompt ships |
| PostgreSQL full-text / explicit relationships | Baseline | First artifact retrieval |
| pgvector | Conditional | Labeled retrieval tests show a semantic recall gap |
| CloudWeGo Eino | Conditional | AI-internal graph/agent control flow becomes complex enough to justify framework |
| LangGraph | Conditional alternative | Team accepts Python/JS subservice and LangGraph solves a concrete use case |
| Braintrust / Langfuse | Deferred vendor decision | Hosted UI/datasets/experiments are valuable and data policy is approved |
| Mem0 / Zep / other memory stores | Not for core platform | A distinct conversational/personalization use case is defined |
| MCP server | Conditional integration | An LLM client must discover/use approved platform tools |
| LiteLLM or model gateway | Deferred | Multiple providers or centralized proxy policy justify another runtime |
| Separate graph DB / vector DB | Deferred | Query volume/relationship complexity or retrieval evaluation demonstrates need |
| Multi-agent supervisor/autonomous loop | Not initially | A benchmarked task cannot be handled more simply and boundedly |

## Approval rule
Do not install a tool because it appears in an ecosystem diagram. Record the concrete problem it solves, alternatives, measured benefit, operational/hosting implications, data exposure, and exit strategy before adding it.
