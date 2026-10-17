## Specification and tests

- [x] 1.1 Add RED-first mutation tests for missing, malformed, duplicate, and mismatched artifact/evidence/observation/finding references.
- [x] 1.2 Add a positive test that preserves exact source artifact digests and locators.

## Implementation

- [x] 2.1 Validate a unique per-run artifact index with safe paths and SHA-256 digests.
- [x] 2.2 Require evidence and observation artifact ID/path/hash joins to match exactly.

## Verification

- [x] 3.1 Demonstrate RED then GREEN and run focused Pages exporter tests.
- [x] 3.2 Run the full deterministic suite, strict MkDocs build, and OpenSpec validation.
- [x] 3.3 Review the private-data failure mode and confirm no public or PR build can export ledger data.
