# Pathfinder evidence normalize

## Why

Pathfinder validates observations inside `pkgcollect` as opaque maps. That gate binds digests and typed locators, but it does not expose a dedicated normalize stage: no `locator_precision`, no canonical ordering contract, and no reusable conflict classification before evaluation. The OTEL/dashboard work landed separately; evidence normalize is the next deterministic slice that makes provenance rules testable and shareable across intake, paste extraction, and evaluate.

## What changes

- Add a pure Go `evidence` normalize package that turns package-scoped artifacts and raw observations into a canonical observation list.
- Derive `locator_precision` (`EXACT` | `APPROXIMATE` | `UNAVAILABLE`) from locator shape without inventing spans.
- Canonical-sort observations before handoff so hashes, prompts, and evaluations are order-stable.
- Classify predicate+subject value conflicts without inventing or dropping authored observations (evaluation remains fail-closed / inconclusive).
- Keep `pkgcollect.CollectObservations` as the package adapter: verify artifacts, consult the predicate registry, then call normalize.
- Do not call models; do not synthesize missing observations.

## Non-goals

- Full `EvidenceItem` / Protobuf evidence API from `docs/contracts/EVIDENCE.md`.
- Relation-to-claim, retrieval-method registry, or excerpt redaction policy.
- Changing paste conflict drop behavior or requirement-engine outcome vocabulary.
- Database-backed evidence store or enterprise catalog migration.

## Acceptance criteria

- Normalize rejects fabricated or incomplete provenance (missing required fields, unknown predicate when registry supplied, digest mismatch path stays in collect).
- Every accepted observation carries a valid `locator_precision`.
- Shuffled input observation order yields identical canonical output order and fingerprint.
- Conflicting values for the same predicate+subject are reported by a pure classifier; collect still returns the observations so the engine can mark `conflicting_evidence`.
- Go unit tests cover precision derivation, sort stability, conflict classification, and registry/value-type failures.
- OpenSpec validates for this change.

## Risks and rollback

- Adding fields to observation maps is additive for the engine (it ignores unknown keys). Rollback removes the package and restores inline `pkgcollect` validation.
- Over-strict precision rules could mark paste spans `APPROXIMATE`; tests pin the allowlisted kinds.

## Owner decisions captured

- Normalize is a functional-core stage over explicit package/artifact snapshots; registry lookup stays at the collect adapter boundary.
- Conflicts are classified, not silently resolved, at normalize time.
