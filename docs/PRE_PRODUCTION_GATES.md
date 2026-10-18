# Pathfinder pre-production gates

This is the release checklist for moving Pathfinder from synthetic demonstrations to any production source integration. Passing unit tests is necessary, not sufficient. A gate is **open** until its required evidence is reviewed and recorded; a green workflow must not imply that detector quality or production readiness has been established.

## Current boundary

The current detector and review path is an offline prototype using synthetic fixtures and deterministic cue rules. The evaluation corpus is small and scenario-specific. The local JSONL review ledger is single-host demo storage; GitHub issues are review intake, not the authoritative ledger. No production repository, event stream, Aurora database, or live runtime has been validated by this checklist.

## Gates

### G1 — Applicability and retrieval

**Required evidence**
- Explicit `in_scope`, `out_of_scope`, and `uncertain` outcomes with reason codes.
- Tests for active/retired ADRs, conditional scope, metadata gates, no-match, retrieval miss, conflicting candidates, and stale sources.
- No-match is never silently interpreted as compliant.
- The ADR applicability decision is recorded separately from the implementation compliance decision.

**Exit condition:** all supported source types pass the applicability suite, and unresolved applicability remains visible to reviewers.

### G2 — Detector evaluation

**Required evidence**
- A versioned, adjudicated evaluation corpus with source provenance and scenario coverage.
- A separately stored, access-controlled holdout that is excluded from tuning, review-feedback promotion, and routine developer inspection.
- Metrics include precision, recall, false-positive rate, missed-deviation rate, inconclusive rate, and per-scenario breakdowns.
- Results distinguish the probability sample from the risk-triage queue; only the former supports population estimates, using its inclusion weights.
- Thresholds are approved before evaluating the holdout and are not retrofitted to a small sample.

**Exit condition:** reviewers approve the corpus and thresholds, and an independent holdout report meets them. Until then, all quality figures are provisional.

### G3 — Evidence and finding contracts

Every finding must identify:
- The ADR ID, version, lifecycle state, and applicable requirement.
- The subject and immutable source snapshot or document revision.
- Evidence IDs, source locators/spans where available, content hashes, and typed requirement-to-observation relationships.
- The assessment outcome and explicit limitations/counter-evidence gaps.
- Analysis run ID, detector/rule/model version, input fingerprints, and timestamps.
- Review disposition and adjudication state as separate fields from the detector outcome.

**Exit condition:** schema validation and contract tests reject missing provenance, unknown evidence references, invalid relationships, and unsupported conclusions.

### G4 — Human review and feedback

**Required evidence**
- Deterministic sample frame fingerprint, seed, stratum counts, inclusion probabilities, and design weights.
- Risk triage remains a separate, unweighted queue.
- Stable review-unit IDs and idempotent issue creation/reconciliation.
- Reviewer dispositions are append-only events; corrections supersede earlier events rather than rewrite them.
- Only approved, adjudicated feedback can become an evaluation candidate.
- Holdout IDs are rejected by feedback promotion.

**Exit condition:** an end-to-end test proves comparison → sample → review intake → disposition → adjudication → evaluation candidate, including retry and duplicate delivery cases.

### G5 — Verification, replay, and resilience

**Required evidence**
- Deterministic AST/configuration/policy checks run before model inference where applicable.
- The verifier checks counter-evidence and validates every cited evidence ID against the supplied evidence set.
- Source comments and documents are treated as untrusted data, not instructions.
- Unresolved dynamic dispatch, missing runtime evidence, contradictory sources, and stale locators lead to an inconclusive result where appropriate.
- Replaying identical versioned inputs produces the same deterministic artifacts; retries do not create duplicate review units.
- Partial failures, interrupted runs, and changing ADR versions have defined recovery behavior.

**Exit condition:** replay and fault-injection tests pass, and no result is represented as runtime proof unless runtime evidence exists.

### G6 — Security and operations

**Required evidence**
- Threat model and trust-boundary review for source ingestion, documents, model providers, CI identities, and review storage.
- Repository/tenant isolation, least-privilege credentials, secret handling, retention/deletion, and evidence redaction requirements.
- Audit integrity requirements that go beyond a local hash chain when production use requires external anchoring.
- Timeouts, bounded retries, resource limits, model-call budgets, and safe degraded behavior.
- Metrics for queue age, failure rate, evidence coverage, inconclusive rate, cost per analysis, and review backlog.
- Recovery and incident procedures plus explicit service-level objectives.

**Exit condition:** security and operations owners accept the documented controls and demonstrate recovery behavior in a non-production environment.

## Rules for claiming readiness

- A passing CI run proves only that the checks in that run passed.
- Synthetic fixture success is not production integration evidence.
- Evidence-strength bands are not calibrated probabilities of correctness.
- No automatic waivers, finding closure, or self-training.
- Do not merge a detector or policy change that regresses the locked evaluation report.
- Do not enable a production connector until all six gates have reviewed evidence and named approval.

## Current status

All six gates remain **open** pending their required evidence. This is deliberate: this document records the bar, not a claim that Pathfinder has met it.
