# Design: Token-level entropy detection with structural preservation

The existing redactor first replaces quoted literals and matches known credential formats, then applies an entropy score to the complete remaining string. Apply entropy detection to opaque token-shaped spans instead of the complete string. Keep the existing known-pattern checks across the full text so formats such as bearer credentials and AWS keys remain covered. Exempt well-formed SHA-1/SHA-256 digests because they are provenance values, not credentials.

This preserves punctuation-separated source identifiers and function names while still finding a random credential embedded beside ordinary text. Tests must cover both sides of that contract, then the real Go fixture must prove that `callgraph.json` retains the exact resolved provider symbol and pinned source reference.

## Behavioral proof

- Python regression tests for opaque-token redaction, hash preservation, and long qualified call-edge identifiers.
- Run the Go fixture end to end and inspect the generated callgraph for the provider callee, reachability, resolution metadata, and pinned source reference.
- Run the remote GitHub language-validation matrix after the fix; report each language result separately.
