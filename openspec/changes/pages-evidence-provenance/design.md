# Design: validate provenance joins before Pages projection

Build a per-run artifact index keyed by `artifact_id`, after validating unique non-empty IDs, normalized relative paths, and lowercase 64-character SHA-256 values. Reject duplicate artifact paths when they make a path-only reference ambiguous.

For each exported evidence row, require an artifact ID in the index and require its path to equal the indexed artifact path. The evidence row's `sha256` is the excerpt digest, not the source artifact digest: validate its format and recompute it from the stored excerpt before redaction. The projection should retain the artifact's source digest, recorded excerpt digest, and displayed excerpt digest separately.

For each exported observation, parse `source_ref_json` and require `artifact_id`, `path`, and `sha256` to match the artifact index exactly. Preserve the locator and redaction behavior. Do not turn a failed reference into an empty hash or silently omit it.

For each projected finding, parse its evidence ID list. A non-inconclusive outcome must cite at least one ID. Every cited ID must resolve to an evidence row included in the bounded projection; otherwise fail rather than display a detached conclusion.

## Test mapping

- Mutation tests corrupt each side of the artifact/evidence/observation join and assert a clear `ValueError`.
- An evidence excerpt canary verifies that the stored excerpt digest is checked before text redaction and the displayed digest is calculated after redaction.
- A positive test asserts the projected hashes match the full artifact digest.
- Existing canary-redaction, output-bound, clone-identity, and visibility-gate tests remain regression coverage.
