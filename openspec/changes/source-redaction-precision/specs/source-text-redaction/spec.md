## ADDED Requirements

### Requirement: Redaction preserves structured source evidence
Source-text redaction MUST remove quoted literals and recognized credential patterns. Entropy-based checks MUST target opaque token-shaped spans rather than classify an entire structured source expression by its aggregate entropy. Provenance hashes and qualified code identifiers MUST remain available to evidence validation and audit display.

#### Scenario: Opaque credential appears inside surrounding text
- GIVEN a long opaque high-entropy token appears beside ordinary source text
- WHEN the redactor processes the text
- THEN the token is removed or the containing sensitive text is replaced
- AND the token is absent from persisted evidence

#### Scenario: Qualified symbol has high aggregate entropy
- GIVEN a long qualified function name contains package, receiver, and method syntax
- WHEN the callgraph is redacted and normalized
- THEN the exact qualified caller and callee remain available
- AND the edge retains its pinned artifact, source path, and line locator

#### Scenario: Provenance digest is present
- GIVEN an artifact SHA-256 value is present in a structured observation
- WHEN source-derived values are redacted
- THEN the lowercase hexadecimal digest remains unchanged
