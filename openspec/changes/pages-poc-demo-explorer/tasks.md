## Specification and behavior proofs

- [x] 1.1 Add regression tests for the synthetic snapshot allowlist, path boundary, and generated run provenance.
- [x] 1.2 Add browser-core tests for public run/job responses, safe URLs, output escaping, API errors, selected attempts, and bounded history.
- [x] 1.3 Add docs contract tests for workflow links, stage controls, score caveat, accessibility, and generated snapshot path.
- [x] 1.4 Add tests for CSV projection redaction, output bounds, source-path traversal, and private Pages visibility/opt-in gates.
- [x] 1.5 Add tests that clone identity controls internal Actions links and that private ledger access is excluded from pull-request runs.

## Implementation

- [x] 2.1 Implement versioned fixture and run-history projections with explicit fields, bounded records, pinned hashes, and source-text redaction.
- [x] 2.2 Add browser-side read-only workflow history with bounded API requests and text-only DOM rendering.
- [x] 2.3 Add accessible animated pipeline exploration for evidence, observations, confidence, and coverage.
- [x] 2.4 Integrate the demo into MkDocs and generate fixture data from the deterministic mock analysis in the Pages workflow.
- [x] 2.5 Add fail-closed private/internal Pages checks and exact opt-in for actual CSV records; exclude pull-request events from the real-data step.
- [x] 2.6 Make Pages and Actions links resolve against the private organization clone.
- [x] 2.7 Resolve the tracked case-only architecture-document collision without dropping the existing page content.

## Verification

- [x] 3.1 Demonstrate failing clone-identity behavior test, then pass after tightening repository validation.
- [x] 3.2 Run all deterministic PoC Python tests, browser-core Node tests, OpenAPI validation, and strict MkDocs build.
- [x] 3.3 Verify canary evidence literals are redacted, no raw artifacts are exported, and public builds stay fixture-only unless private gates pass.
- [x] 3.4 Validate this change and all active OpenSpec changes; review deployment state and describe what still requires the private-clone owner.
