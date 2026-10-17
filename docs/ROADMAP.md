# Implementation roadmap

This is a proposed sequence; it does not imply work has shipped.

## Phase 0 — Confirm design and bootstrap
- Complete the [Pre-implementation readiness milestone](PRE_IMPLEMENTATION_READINESS.md).
- Review and disposition the [MVP decision packet](MVP_DECISION_PACKET.md).
- Review the [requirements-to-proof matrix](REQUIREMENT_TO_PROOF_MATRIX.md) and synthetic [evaluation corpus](evaluation/STARTER_CORPUS.md).
- Review the baseline and mark choices accepted/rejected/open.
- Decide whether the initial consumer requires a gRPC API or whether webhook-only HTTP/Lambda is enough for MVP.
- Confirm API hosting profile (ECS/Fargate + ALB for gRPC, or serverless HTTP).
- Install current OpenSpec and Buf tooling.
- Pin tool/plugin versions and run Protobuf formatting/lint/build; decide generated-code policy.
- Pick the first input type and comparison mode.
**Exit:** reviewed vertical-slice change, API boundary decision and test plan.

## Phase 1 — Thin vertical slice
- Go module, CI, config, structured logging and secret handling.
- Accept one code diff and one known ADR.
- Build deterministic evidence with exact source refs.
- Call Anthropic directly through a small adapter.
- Validate typed output and reject unknown evidence IDs.
- Persist a job/result and make it inspectable.
- Create a small labeled evaluation set.
**Exit:** every finding is traceable; tests cover deviation, non-deviation, irrelevant ADR and insufficient evidence.

## Phase 2 — Artifact and decision model
- Add immutable artifact versions and hashes.
- Normalize ADR status, scope, supersession and relationships.
- Ingest technical specifications.
- Add idempotency, authorization, audit events and migrations.
**Exit:** provenance survives updates and replays.

## Phase 3 — Distributed execution and API
- Add Step Functions and reusable Go Lambda workers.
- Implement deadlines, bounded retries, parallel stages, terminal failures and replay.
- If the gRPC boundary is approved, implement the long-lived Go gRPC API and generated clients, with auth/status/health/deadline handling. Otherwise use HTTP ingress for webhook/API needs.
- Add S3 for large artifacts and operational telemetry where required.
**Exit:** duplicate events and transient failures are safe; API contract is tested and compatibility-checked.

## Phase 4 — Three comparisons and retrieval
- Add specification ↔ ADR and specification ↔ implementation.
- Improve exact/metadata/full-text retrieval; add embeddings only if eval justifies them.
- Add code language adapters based on pilot needs.
**Exit:** each comparison mode has its own benchmark.

## Phase 5 — Quality and review
- Expand labeled/adversarial evaluation corpus.
- Add selective independent verification, human disposition and regression gates.
- Establish measured thresholds for precision, recall, evidence validity, cost and latency.
**Exit:** quality standards are reviewed and met.

## Phase 6 — Integration and controlled enforcement
- Add GitHub checks/comments or other integrations.
- Recheck source freshness before publishing.
- Keep merge blocking disabled until policy approves thresholds and override behavior.
- Add SLAs, retention rules and incident runbooks.
**Exit:** users trust the results and integrations are governed.

## Deferred
Dedicated conversational memory, separate graph DB, autonomous multi-agent loops, A2A, automatic remediation and automatic ADR changes. LangGraph remains optional for bounded AI sub-workflows only if a concrete need is demonstrated.
