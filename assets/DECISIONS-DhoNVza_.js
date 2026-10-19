const e=`# Decision log

These are interim planning choices. **Recommended** means a proposed default; it is not an accepted enterprise ADR. Review and record formal decisions when approved.

## D-001 — Go-first application
**Status:** Recommended. Use Go for API, deterministic workers, persistence, orchestration adapters and AI harness. Use another language only behind a boundary when a capability materially warrants it.

## D-002 — Direct Anthropic API
**Status:** Confirmed direction. Call Anthropic directly, not Bedrock. Isolate provider-specific behavior behind an adapter. Model selection, data handling, limits and billing still need confirmation.

## D-003 — Step Functions owns distributed orchestration
**Status:** Recommended. Use Step Functions for the top-level asynchronous lifecycle when work is distributed across Lambda workers. Do not let a gRPC API or LangGraph take ownership of that same workflow.

## D-004 — Evidence-first hybrid analysis
**Status:** Core design principle. Gather deterministic source evidence, use bounded AI assessment, validate in application code.

## D-005 — No mandatory agent framework
**Status:** Recommended. No LangGraph/LangChain requirement for the first vertical slice. Reconsider only if conditional reasoning/checkpointing becomes a demonstrated need.

## D-006 — No dedicated conversational-memory product initially
**Status:** Recommended. Architectural knowledge remains source-versioned artifacts, relationships and derived indexes.

## D-007 — PostgreSQL first; vector retrieval optional
**Status:** Recommended. PostgreSQL/Aurora is authoritative. pgvector and a separate graph DB require measured justification.

## D-008 — Human review before enforcement
**Status:** Recommended. Start advisory/shadow; no AI-only merge blocking.

## D-009 — OpenSpec for behavior changes
**Status:** Recommended. Use proposal/spec/design/tasks, reviewed implementation, verification and archive.

## D-010 — Immutable provenance
**Status:** Core design principle. Findings bind to exact source versions; summaries and search indexes are derived.

## D-011 — Reusable workers, not dynamically created Lambda
**Status:** Recommended. Deploy known narrow workers and invoke them as needed.

## D-012 — Contract-first Protobuf and a bounded gRPC boundary
**Status:** Proposed in OpenSpec change grpc-protobuf-contracts; not yet implementation-approved.
**Proposal:** Define the platform's typed control-plane contract in Protobuf and use gRPC for synchronous job-control APIs if a long-running API service is justified. Keep job execution in Step Functions and invoke Lambda workers directly. Do not put a gRPC listener in Lambda.
**Trade-off:** strong typed contracts/generated clients and schema compatibility checks versus an always-on service, ALB/network/auth/rollout complexity. A serverless webhook-only MVP may defer the gRPC server while retaining Protobuf schemas.
**Review:** Decide whether the gRPC endpoint is in the MVP before implementing deployment infrastructure.

## D-017 — Functional core / imperative shell
**Status:** Recommended engineering pattern, pending review. Keep domain policy/evidence transformations pure where practical, isolate infrastructure/clock/random/model effects at explicit boundaries, use stable ordering and make external operations idempotent.  
**Rationale:** Reproducible tests, safe replay and reduced hidden coupling without forcing a functional runtime or custom monad abstractions.

## Change control
Record date, owner, rationale, alternatives, consequences and links to OpenSpec/ADR when status changes. Do not silently turn recommendations into constraints.
`;export{e as default};
