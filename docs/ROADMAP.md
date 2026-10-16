# Implementation roadmap

This is a proposed sequence; it does not imply work has already shipped.

## Phase 0 — Confirm design and bootstrap
- Review this baseline and mark choices accepted/rejected/open.
- Install current OpenSpec tool integration.
- Pick the first input type and comparison mode.
- Confirm pilot scope, authorization model and data handling.
**Exit:** a reviewed vertical-slice change and test plan.

## Phase 1 — Thin vertical slice
- Go module, CI, configuration, structured logging and secret handling.
- Accept one code diff and one known ADR.
- Build deterministic evidence with exact source refs.
- Call Anthropic directly through a small adapter.
- Validate typed output and reject unknown evidence IDs.
- Persist a job/result and make it inspectable.
- Create a small labeled test/evaluation set.
**Exit:** every finding is source-traceable; tests cover deviation, non-deviation, irrelevant ADR and insufficient evidence.

## Phase 2 — Artifact and decision model
- Add immutable artifact versions and hashes.
- Normalize ADR status, scope, supersession and relationships.
- Ingest technical specifications.
- Add idempotency, authorization, audit events and database migrations.
**Exit:** provenance survives updates and replays.

## Phase 3 — Distributed execution
- Add API/webhook ingress, Step Functions and reusable Go Lambda workers.
- Add deadlines, bounded retries, parallel work, terminal failure and replay.
- Add S3 for large artifacts if needed and operational telemetry.
**Exit:** duplicate events and transient failures are safe.

## Phase 4 — All three comparisons and retrieval
- Add specification ↔ ADR and specification ↔ implementation.
- Improve exact/metadata/full-text retrieval; add embeddings only if eval justifies them.
- Add code language adapters based on pilot needs.
**Exit:** each comparison mode has a separate benchmark.

## Phase 5 — Quality and review
- Expand labeled/adversarial evaluation corpus.
- Add selective independent verification, human disposition and regression gates.
- Establish measured thresholds for precision, recall, evidence validity, cost and latency.
**Exit:** quality standards are reviewed and met.

## Phase 6 — Integration and controlled enforcement
- Add GitHub checks/comments or other integrations.
- Recheck source freshness before publishing.
- Keep merge blocking disabled until policy explicitly approves thresholds and override behavior.
- Add operational SLAs, retention rules and incident runbooks.
**Exit:** users trust the result and the integration is governed.

## Deferred
LangGraph, dedicated memory, separate graph DB, autonomous multi-agent loops, A2A, automatic remediation and automatic ADR changes. Reconsider only after a concrete requirement and measured benefit.
