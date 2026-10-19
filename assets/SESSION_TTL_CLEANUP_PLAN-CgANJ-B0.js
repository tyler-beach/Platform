const e=`# Session TTL contract cleanup plan

## Goal
Make the offline session-TTL vertical slice auditable and hard to misinterpret without expanding it into production integrations.

## Scope and sequence

### P0 — Input and decision correctness
- Validate the top-level case type, artifact shape, status/scope fields, evidence records, locator fields, and CLI JSON shape.
- Distinguish considered evidence IDs from accepted evidence IDs and rejected observations; attach explicit rejection reason codes instead of silently dropping invalid values.
- If any decision-relevant TTL observation is rejected, force an inconclusive result even when another observation is valid, so partial invalid evidence cannot produce an overconfident compliance/deviation claim.
- Keep invalid, missing, conflicting, and not-applicable outcomes distinct. Never infer compliance from absent or invalid evidence.
- Keep policy threshold provenance explicit: policy v1 is fixed at 600 seconds; ADR text is pinned but is not dynamically interpreted by this evaluator.

### P1 — Evidence and result contracts
- Extract JSON Pointer resolution into a focused helper with strict RFC 6901 escape and array-index handling.
- Validate TTL evidence against the exact pinned source revision and resolved value.
- Define a stable result shape with explicit outcome, relationship, applicability, evidence references, rejected-observation reasons, uncertainty, policy identity, and deterministic fingerprint.
- Fingerprint the complete result payload before adding the fingerprint field.

### P1 — Maintainability
- Remove unused outcome constants and misleading parser-version naming.
- Split input validation, evidence resolution, decision evaluation, result assembly, and fingerprinting into small functions; avoid class hierarchies and unnecessary dependencies.

### P2 — Regression and CLI coverage
- Test malformed JSON and malformed case shapes, pointer edge cases, bool/int confusion, negative/floating values, missing and conflicting observations, threshold override attempts, stale hashes/revisions, and replay determinism.
- Exercise CLI success and failure behavior, including non-zero exits for malformed input.
- Run targeted tests and the repository's relevant CI checks against the exact PR head.

## Acceptance criteria
- No invalid/missing observation can yield a clean-compliance result.
- Every decision-relevant observation is accounted for, with a machine-readable exclusion reason when it is not usable.
- Policy parameters and pinned artifact revisions are included in the result fingerprint.
- CLI errors are actionable and do not emit tracebacks for ordinary invalid input.
- The PR stays isolated from \`main\` until review and checks are complete.

## Explicit non-goals
No Aurora/Bedrock integration, live source adapters, arbitrary ADR semantic extraction, model calls, or production accuracy claims in this cleanup.
`;export{e as default};
