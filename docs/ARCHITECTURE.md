# Architecture overview

## Recommended target
Go-first application and deterministic workers; AWS Step Functions as the top-level distributed workflow owner; reusable AWS Lambda workers for bounded jobs; direct Anthropic API calls through a provider adapter; PostgreSQL/Aurora PostgreSQL for authoritative relational state; S3 for immutable source snapshots or large artifacts as needed. pgvector is optional and should be added only if retrieval evaluation demonstrates value. This is a target recommendation, not a deployed design.

## Logical components
- **Ingress/job creation:** accept repository events, submitted diffs, spec documents or API requests; authenticate, authorize, validate size/shape, assign idempotency identity, and preserve source versions.
- **Artifact normalization:** standardize code/spec/ADR inputs while preserving source URI, commit/ref or document version, content hash, path/line/symbol/section, owner, timestamps and status.
- **Context resolution:** discover candidate ADRs and requirements through structured metadata, explicit relationships, identifiers, code symbols, full-text search and optionally semantic search.
- **Deterministic analysis:** diff processing, AST/symbol analysis, document parsing and explicit checks create evidence before a model is called.
- **Evidence package assembly:** build the smallest sufficient package for one comparison mode, with stable IDs and source-version bindings.
- **AI assessment:** invoke Anthropic with a versioned prompt and output schema, explicit budgets, deadline and purpose.
- **Verification:** validate schema, evidence IDs, source versions, decision status/applicability and domain invariants. Use a second model call only when evaluation shows it helps on ambiguous/high-impact cases.
- **Persistence/delivery:** store findings, provenance, job/run metadata, verification and review state; expose results through an API or later repository/CI integrations.

## Patterns to use
- **Pipeline / staged processing:** each stage has one responsibility and typed input/output.
- **Ports and adapters:** domain logic does not depend directly on AWS SDK or Anthropic request types.
- **Immutable evidence artifacts:** source versions and stage outputs are addressable by IDs/hash.
- **Explicit state machine:** lifecycle transitions are modeled, not inferred from logs.
- **Fan-out/fan-in:** independent code analysis and context retrieval can run in parallel, followed by one aggregation step.
- **Hybrid rules + AI:** deterministic checks handle clear predicates; models handle ambiguity and semantic comparison.
- **Idempotent workers:** reprocessing the same stage input does not duplicate effects.
- **Append-oriented audit trail:** record stage transitions, retries, findings, publishing and human dispositions.
- **Human in the loop:** ambiguous or high-impact findings route to review.
- **Transactional outbox if needed:** add only if reliable domain-write/event-publish consistency becomes a concrete requirement.

Avoid a giant mutable “blackboard” of unversioned context. Prefer versioned job state and immutable stage artifacts with explicit dependencies.

## Orchestration
Step Functions should own the distributed job lifecycle: branching, retries, timeouts, parallel branches and human approval waits. Go functions own task logic. Do not use Step Functions and LangGraph as competing owners of the same job.

LangGraph is optional for a bounded AI sub-workflow if conditional reasoning loops, checkpointing or interruption/resumption become hard to manage directly. It is not required for invoking tools or non-LLM functions.

## Candidate AWS footprint
API Gateway or controlled ingress; Go Lambda; Step Functions; Aurora/PostgreSQL; S3 where needed; Secrets Manager; IAM; CloudWatch; OpenTelemetry-compatible tracing/export. Add SQS/EventBridge if buffering or event distribution needs them. Avoid infrastructure/services before a requirement exists.

## Failure policy
Each worker returns a typed result or classified error. Retry transient failures with bounded backoff; do not blindly retry invalid input, authorization failures, unsupported types, stale references or deterministic validation failures. Jobs terminate as completed, review-required, failed, cancelled or expired.

See docs/diagrams/architecture.md, docs/DATA_MODEL.md and docs/OPERATIONS.md.
