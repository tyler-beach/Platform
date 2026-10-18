# Session TTL adversarial assurance plan

## Goal
Treat the offline session-TTL evaluator as an untrusted-input boundary. Prevent false confidence, provenance drift, nondeterministic results, and regressions without expanding the reference slice into production integrations.

## P0 — Hostile input and schema boundaries
- Validate top-level and nested types before set membership or other operations that can raise incidental exceptions.
- Exercise null/scalar/list/object substitutions, duplicate JSON keys, malformed locators, missing fields, and malformed CLI input.
- Exercise JSON Pointer root/empty pointer, escaped tokens, empty member names, scalar traversal, array bounds, dash, negative, and non-canonical indices.
- Expected input/IO failures must exit non-zero with actionable errors, not tracebacks.

## P0 — Evidence provenance and integrity
- Pin artifact content by SHA-256 and revision; require evidence to resolve to the exact pinned source value.
- Attack unknown/duplicate references, stale revisions, ambiguous artifact IDs, malformed source JSON, duplicate source keys, and bool-versus-int confusion.
- Keep considered, accepted, and rejected observations explicit, with machine-readable rejection reasons.

## P0 — Decision boundary and false confidence
- Cover boundary values 0, 599, 600, 601, negative, float, bool, absent, and conflicting observations.
- Invalid decision-relevant evidence must force an inconclusive result even when a valid observation exists.
- Non-applicable cases must never claim compliance or deviation; outcomes and relationships must agree.

## P1 — Result contract and replay integrity
- Validate schema/policy/normalization versions, policy parameters, pinned input identities/digests, evidence accounting, applicability, relationship, and outcome consistency.
- Malformed result fields must raise controlled ValueError rather than accidental TypeError.
- Verify repeated evaluation is deterministic and input/result mutations are reflected in fingerprints.

## P1 — Pipeline and trust boundaries
- Document normalized input as the contract; do not treat model summaries as evidence or allow caller-supplied policy thresholds.
- Preserve evidence IDs, provenance, uncertainty, and rejection reasons in output.
- Keep production adapters, Aurora/Bedrock integration, and arbitrary ADR semantic interpretation out of this slice.

## P2 — Mutation and operational hardening
- Add regression tests for hash tampering, changed result fields, duplicate keys, malformed JSON, bad paths, and invalid result payloads.
- Review CI/release gates against the exact PR head. Use mutation/property-based tooling only if available and actually executed; do not imply those tools ran otherwise.

## Acceptance criteria
- Invalid or missing evidence never becomes a clean result.
- Every considered TTL observation is accepted or rejected with a reason; mixed valid/invalid observations remain inconclusive.
- Result validation rejects malformed and internally contradictory payloads cleanly.
- Policy, artifact revision, evidence accounting, and result fingerprint remain deterministic and auditable.
- The exact PR head passes the relevant automated checks before merge.

## Explicit non-goals
No production connectors, Aurora/Bedrock access, arbitrary ADR language interpretation, model-based extraction, or production-readiness claim.
