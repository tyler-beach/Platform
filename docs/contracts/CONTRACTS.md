# Data contracts and invariants

**Status:** First-pass proposed contract. This is a design baseline, not a claim that persistence or runtime validation is implemented. Protobuf is authoritative for the public gRPC control plane; OpenAPI defines the proposed HTTP/JSON façade. This document specifies semantic invariants schemas cannot fully express.

## Contract principles

1. **Stable identity is not content identity.** An artifact ID identifies a logical source; an artifact-version ID and/or digest identifies the exact version analyzed.
2. **Historical runs are immutable in meaning.** New ADR status, scope, extraction, or code changes must not silently rewrite evidence or interpretation used by a prior job.
3. **Outcomes are not execution states.** A job can fail technically without a finding; an inconclusive finding is not a failed job.
4. **Severity, outcome, validation, and review are independent axes.** Do not collapse them into one score or generic risk enum.
5. **References must resolve within the authorized workspace and evidence package.** Caller- or model-supplied IDs are never authorization grants.
6. **Untrusted content remains data.** Source text and model output cannot modify policy, permissions, orchestration state, or tool access.
7. **No lossy overwrite.** Preserve source references, audit history, and review history when updating derived indexes or re-running analysis.

## Common scalar conventions

| Concept | Contract |
|---|---|
| Identifier | Opaque, non-empty string. Clients must not parse internal structure. UUID is acceptable internally but not required by this first pass. |
| Timestamp | UTC RFC 3339 / protobuf Timestamp. Server-generated except explicitly documented client event times. |
| Digest | Lowercase hexadecimal SHA-256, 64 characters. Define exactly which byte representation is hashed. |
| Source location | Paths and symbols use the source adapter's canonical form. Line numbers are one-based and end-inclusive. |
| Optional field | Absence means unknown/not supplied unless the field contract says otherwise. Do not overload empty string or zero with several meanings. |
| Enum | Unspecified is invalid for fields required to make a decision. Handle unknown enum values safely for forward compatibility. |
| Collection order | Sort before hashing, prompting, or stable serialization. Use stable pagination order for a fixed result snapshot. |
| Text | UTF-8. Apply field-specific maximums at ingress and storage boundaries. Treat source-derived text as untrusted. |

Recommended initial limits, to be configurable and ratified before production: 100 input artifact references/job; 100 findings/page by default, hard maximum 500; 100 evidence references/finding; claim 2,000 characters; rationale 12,000 characters; review reason 4,000 characters; idempotency key 8–200 visible ASCII characters. Reject oversized payloads rather than silently truncating provenance.

## Core domain types

### Workspace

Authorization and data-isolation boundary. It scopes artifacts, jobs, findings, reviews, audit events, and idempotency keys.

- Every persisted tenant-owned row/object has exactly one workspace owner, directly or through a parent with enforced foreign-key and authorization checks.
- Every read/write checks authenticated identity and workspace membership server-side.
- Changing an ID, URI, repository slug, or pagination token must never cross workspace boundaries.
- A single-tenant deployment still uses the workspace model; single-tenant is a deployment profile, not a schema shortcut.

### Artifact

Logical source identity, such as an ADR file, technical specification, repository, API contract, or code-change request.

Required fields: artifact ID, workspace ID, kind, canonical source identity/URI, source-system type, creation timestamp. Optional metadata: owner, repository/ref, display name, tags.

- Artifact identity remains stable across versions; changed source content creates or references another ArtifactVersion.
- Source URI is a locator, never authorization.
- The source adapter owns canonicalization and prevents path traversal and unsafe remote fetches.
- Retention must distinguish logical tombstones from deletion of immutable snapshots.

### ArtifactVersion

Immutable content/source version for an Artifact. Includes version ID, artifact ID, revision token (e.g. commit SHA or document version), content SHA-256 when available, ingest timestamp, extractor/normalizer version, and addressable locations.

- Version ID plus workspace/artifact identity resolves to one immutable version.
- A code change binds to base and head revisions; a moving branch name alone is not immutable.
- If a content digest is present, its byte-normalization rule is explicit and stable.
- An unavailable or unverifiable source version produces an explicit incomplete/inconclusive state; do not silently substitute current content.
- Derived text, embeddings, parsed ASTs, and indexes are disposable derivatives labelled with source and indexer versions.

### Decision (ADR) and Requirement

A Decision is a normalized representation of an architectural decision, including source artifact-version, stable decision ID, lifecycle status, scope/applicability, effective/superseded relationships, and source spans. A Requirement is an extracted normative/descriptive statement with stable requirement ID, parent Decision or specification, modality (MUST/SHOULD/MAY/unspecified), text, scope, ambiguity state, and source spans.

- Preserve original wording and exact source spans; normalized text is supplemental.
- Status, scope, effective dates, ownership, and supersession must come from authoritative metadata or reviewed curation, not a model guess.
- Applicability is first-class: applicable, not applicable, or unknown. Semantic similarity alone cannot make an ADR binding.
- Conflicting or ambiguous decision state remains visible and normally requires review.
- Extraction is versioned. Re-extraction creates a new derived revision with provenance; it does not overwrite the old interpretation.

### Relationship

A typed, directed link between domain objects. Initial types: APPLIES_TO, IMPLEMENTS, REFINES, DEPENDS_ON, SUPERSEDES, RELATED_TO, DERIVED_FROM, EVIDENCE_FOR, CONTRADICTS.

Fields: relationship ID, workspace, source object kind/ID/version, target object kind/ID/version, relationship type, provenance (explicit source, rule-derived, model-suggested, human-confirmed), validation metadata where relevant, creation timestamp.

- Endpoints must exist and be authorized within the workspace.
- Preserve the distinction between explicit source relationships and inferred candidates.
- SUPERSEDES and applicability changes require authoritative evidence or human confirmation.
- Store relationship provenance and derivation version; do not promote model-suggested links without validation.

### AnalysisJob

One asynchronous execution over immutable input versions and fixed pipeline/policy configuration.

Public status values align with Protobuf: QUEUED, RUNNING, NEEDS_REVIEW, SUCCEEDED, FAILED, CANCELLED, EXPIRED.

- Creation requires a supported comparison mode and exact artifact references satisfying it.
- Require a client idempotency key scoped by workspace and operation. Same key plus same canonical request returns the same job; same key plus different request returns a conflict.
- Persist job and idempotency state before acknowledging acceptance. Workflow-start races must be recoverable, preferably with an outbox/reconciler pattern.
- QUEUED may transition to RUNNING. Terminal execution states are SUCCEEDED, FAILED, CANCELLED, EXPIRED. NEEDS_REVIEW marks review routing; implementation must define whether orchestration is complete at this state and must never mask a technical failure.
- State transitions are versioned/compare-and-set and audited. A delayed worker cannot move a terminal job backward.
- Store pipeline/policy version, exact inputs, requester/service identity, timestamps, correlation ID, and safe terminal error code. Private diagnostics do not belong in public job responses.
- Cancellation requests stop future work; they cannot roll back completed side effects. Record accepted/refused cancellation and reason.
- Replays must not erase prior attempt metadata.

### EvidenceItem / EvidenceRef

Evidence is a source-version-bound statement or span supporting, contradicting, or contextualizing a claim. EvidenceItem is the internal retrieved content package; API EvidenceRef is the public pointer/provenance summary.

Required internal fields: stable evidence ID, job/workspace, artifact ID and immutable version, source kind, exact location where possible, digest, retrieval method/version, source-integrity state, selection rationale, and role relative to claim.

- Evidence IDs are minted by the application and scoped to a job evidence package.
- Every finding evidence reference resolves within the exact package presented to the validator and to the same artifact version.
- Preserve original location mapping after normalization/chunking. Path-only citations are weaker than version + line/span/symbol/section.
- Do not claim exact citations when mapping is approximate. Record locator precision.
- Do not put full excerpts in public APIs and logs. Evidence detail may be exposed only through a separately authorized interface.
- Stale source, hash validation failure, or invalid line mapping downgrades or rejects the finding.
- Preserve counter-evidence rather than omitting it because it weakens the conclusion.

### Finding

Validated, auditable assessment created from one AnalysisJob. Fields include finding ID, job ID, outcome, severity, review state, claim, rationale, decision/requirement IDs, evidence refs, human-review requirement, validation state, stable fingerprint, and creation time.

Outcomes: DEVIATION_SUPPORTED, POTENTIAL_DEVIATION, NO_DEVIATION_FOUND, INCONCLUSIVE.

- Every finding is tied to one job and exact source versions; factual claims reference evidence.
- NO_DEVIATION_FOUND means no deviation was identified in the reviewed evidence/scope, not global proof of compliance.
- INCONCLUSIVE is used for insufficient/stale evidence, unresolved applicability, conflicting source state, or failed semantic validation. It is not simply low severity.
- Severity is impact; outcome is evidentiary conclusion; validation is application/schema integrity; review is human workflow. Store independently.
- Never expose raw model self-reported confidence as calibrated probability. Any calibrated score requires a versioned calibration and evaluation process.
- Fingerprints include target immutable version(s), applicable decision/policy versions, normalized claim/rule identity, and fingerprint algorithm version. Do not fingerprint on prose alone.
- Findings are immutable snapshots. Review, correction, re-analysis and publication are separately versioned records/events.

### ModelRun

Internal record for one provider/model operation: run/job/attempt ID, provider, operation, model ID/revision when available, prompt ID/version/hash, schema ID/version/hash, input evidence IDs or package digest, request/response provider IDs, token usage, latency, retry attempt, estimated cost/currency, response validation outcome and safe failure category.

- Store only metadata needed for audit/evaluation. Raw prompt/response retention is a separate decision.
- Never log keys, auth headers or unredacted source content as a side effect of ModelRun recording.
- Record configured alias and resolved model ID when available; an alias is not an immutable version.
- Provider failure, timeout, malformed output, refusal and validated assessment are distinct results.
- ModelRun is provenance, not the source of truth for job/finding state.

### BudgetReservation / Usage ledger

A durable reservation for one planned model operation and its eventual usage reconciliation. Suggested fields: reservation ID, workspace/job ID, operation and attempt identity, budget-policy version, model/configuration version, reserved input/output allowance, maximum estimated cost/currency, price catalog version, state, lease/expiry, provider request ID, observed token usage/cost and reconciliation timestamp.

- Budget reservation must be concurrency-safe across independently running workers.
- States should distinguish reserved, settled, released and reconciliation-required/usage-unknown.
- A timeout after a request might have reached the provider must not release the full reservation until safe reconciliation.
- Retry, repair and verifier attempts consume the job's cumulative budget; API retries cannot reset it.
- Actual usage is recorded alongside (not over) preflight estimate. Price/version and estimation method are auditable.
- This ledger is operational accounting metadata, not a calibrated quality/confidence score.

See [AI runtime and token budget contract](AI_RUNTIME.md) for preflight, usage reconciliation, cache semantics and minimum tests.

### Review

Append-only human disposition over a specific finding version: review ID, finding ID/version, workspace, actor, disposition, rationale, timestamp, and optional supporting evidence.

- Review is authenticated/authorized; actor is not inferred from free text.
- A new decision creates a new record/event; it does not overwrite history.
- Re-review references the exact finding version inspected.
- Reviewer disposition does not mutate the original assessment. Expose both the assessment and latest review.
- Any role/second-review policy must be encoded and audited.

### AuditEvent

Durable append-only record of meaningful state or privileged action: actor/service, workspace, event type, object kind/ID/version, timestamp, correlation/trace IDs, outcome, safe reason/code, and schema version.

Minimum categories: job accepted; idempotency reuse/conflict; stage start/complete/failure; retry; cancel requested/accepted/refused; finding created/validated/rejected; review disposition; publication attempted/succeeded/failed; source freshness failure; permission denial as policy requires; administrative changes.

- Write the audit record at the business transaction boundary, or use a transactional outbox for coordinated external effects.
- Workflow history and log aggregation are not the sole audit record.
- No source content, prompt text, secrets or tokens in event attributes.
- Define retention, access, integrity protection and export operationally.

### API error

Public error has stable machine-readable code, safe human-readable message, request ID, retryable flag, and optional bounded violations. HTTP uses RFC 9457-compatible Problem Details with documented extensions; gRPC uses canonical status codes.

- Clients branch on stable codes/statuses, never message text.
- Never return stack traces, internal hostnames, SQL errors, source excerpts, provider bodies, credentials or secrets.
- Retryable is guidance, not a guarantee; use bounded retries, jitter and deadlines.

## Comparison input requirements

| Mode | Minimum input meaning |
|---|---|
| Implementation ↔ ADR | Code change/implementation version and candidate applicable ADR versions. Code changes preserve base and head. |
| Specification ↔ ADR | Technical-specification version and candidate applicable ADR versions. |
| Specification ↔ implementation | Technical-specification version and implementation snapshot/revision with resolvable locations. |

Reject missing or ambiguous required inputs at ingress. Retrieval may discover other candidates, but record the exact versions actually considered.

See also the [AI runtime contract](AI_RUNTIME.md) for model-call budget reservations and usage provenance.\n\n## Data lifecycle\n
Source artifacts/versions are authoritative; extracted decisions, requirements, relationships, embeddings and indexes are versioned derivatives. Job inputs and evidence are immutable snapshots. Findings, ModelRun provenance, reviews and audit events preserve history. Define separate retention/deletion policies for snapshots, transcripts, ordinary logs, audit records, and embeddings before production.
