## Behavior and tests

- [x] 1.1 Add a failing test for high-entropy token detection within surrounding text.
- [x] 1.2 Add a failing test that preserves a long qualified callee and its source reference.
- [x] 1.3 Add a failing test that preserves provenance digests.

## Implementation

- [x] 2.1 Apply entropy checks to opaque token spans and preserve hash-shaped provenance values.
- [x] 2.2 Keep known credential-pattern and quoted-literal redaction intact.

## Verification

- [x] 3.1 Demonstrate RED then GREEN for the new redaction behavior tests.
- [x] 3.2 Run the Go fixture and verify the exact provider callee remains reachable in the audit graph.
- [x] 3.3 Run the complete deterministic test suite and GitHub Actions language-validation matrix.
