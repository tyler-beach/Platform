# Domain model and storage

## Model the source, version and assessment separately
The schema must distinguish original artifacts, immutable versions, extracted interpretation, an analysis run, and the findings from that run.

## Core entities
- **Workspace/Tenant:** authorization and isolation boundary, even if the pilot starts single-tenant.
- **Artifact:** logical source identity, type, canonical URI/path, owner, source system and workspace.
- **ArtifactVersion:** immutable source version, commit SHA/document version, content hash, timestamps, status and source locations.
- **Decision/Requirement:** normalized extracted representation pointing back to exact source version/spans. Preserve source status, modality and ambiguity.
- **Relationship:** source/target/type/provenance for applies-to, implements, refines, depends-on, supersedes and related links.
- **AnalysisJob:** job ID, workspace, idempotency key, comparison mode, actor/event, immutable source versions, status, pipeline version and timestamps.
- **EvidenceItem:** stable ID, artifact version, location, excerpt/hash, retrieval method and selection rationale.
- **Finding:** outcome, severity, claim, rationale, decision/requirement IDs, target version, evidence refs, validation state, review state and dedupe key.
- **ModelRun:** provider/operation/model, prompt/schema version/hash, input evidence IDs, response ID, token usage, latency, retry count, cost estimate and validation status.
- **Review/Feedback:** disposition, actor, timestamp, rationale and exact finding version.
- **AuditEvent:** stage transitions, retries, cancel/publish/review/admin events with trace/correlation IDs.

## Storage recommendation
- **PostgreSQL/Aurora PostgreSQL:** authoritative metadata, jobs, relationships, findings and reviews.
- **pgvector:** optional derived index if semantic retrieval improves evaluated quality.
- **S3:** candidate for immutable snapshots and large normalized artifacts, with hashes, encryption and lifecycle policies.
- **Workflow history:** useful operational context, but not the only long-term audit store.
- **Derived indexes:** rebuildable from source versions and indexer version.

Start with relational relationship tables and indexes; do not add a graph database without a measured need.

## Integrity rules
- Findings refer to exact versions, never only a mutable current document.
- Preserve base/head commit for code changes and content hashes for imported docs.
- Version extraction pipeline and output schema.
- Changes in ADR status/scope can invalidate derived applicability but cannot rewrite historical analysis context.
- Define different retention rules for snapshots, PII, transcripts, audit records and embeddings.

## Proposed finding lifecycle
Candidate → validated → ready-to-publish or needs-review → published → accepted/dismissed/deferred. Failed validation yields rejected/inconclusive, not a confirmed deviation. Ratify state names/transitions before implementation.
