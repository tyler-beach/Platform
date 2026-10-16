# Decision log

These are interim choices from planning. **Recommended** means the proposed default for the first design. It is not an approved enterprise ADR. Record accepted choices formally when reviewed.

## D-001 — Go-first application
**Status:** Recommended. Use Go for API, core, deterministic workers, persistence and AI adapter. Use another language only behind a boundary when a capability materially warrants it.  
**Why:** The problem is largely backend/workflow engineering and Go is the project owner's stated preference.

## D-002 — Direct Anthropic API
**Status:** Confirmed direction. Use Anthropic directly, not Amazon Bedrock. Isolate provider-specific behavior behind an adapter. Model/account/data-handling requirements still need confirmation.

## D-003 — Step Functions owns distributed orchestration
**Status:** Recommended. Use Step Functions for top-level lifecycle when the job is distributed across Lambda workers. Do not allow Step Functions and LangGraph to independently own the same lifecycle.

## D-004 — Evidence-first hybrid analysis
**Status:** Core design principle. Gather deterministic source evidence first, use bounded AI assessment second, validate in application code third.

## D-005 — No mandatory agent framework
**Status:** Recommended. No LangGraph/LangChain requirement for the first vertical slice. Reassess only if conditional reasoning loops/checkpointing become a real need.

## D-006 — No dedicated conversational-memory product initially
**Status:** Recommended. Institutional knowledge should remain in source-versioned artifacts, relationships and derived retrieval indexes—not the model's remembered conversation.

## D-007 — PostgreSQL first; vector search optional
**Status:** Recommended. PostgreSQL/Aurora is authoritative. pgvector and a separate graph database are optional and must be justified by retrieval tests and query needs.

## D-008 — Human review before enforcement
**Status:** Recommended. Start in advisory/shadow mode; do not block merges from unvalidated model output.

## D-009 — OpenSpec for behavior changes
**Status:** Recommended. Plan and review behavior changes with proposal/spec/design/tasks, implementation verification and archive.

## D-010 — Immutable provenance
**Status:** Core design principle. Findings bind to exact source versions; indexes, summaries and embeddings are derived.

## D-011 — Reusable workers, not dynamic Lambda creation
**Status:** Recommended. Deploy known narrow worker functions and invoke them when needed rather than creating functions at runtime.

## Change control
For any status change, record date, owner, rationale, alternatives, consequences and links to the relevant OpenSpec change/ADR. Never turn an open question into a constraint by accident.
