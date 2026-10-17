## Specification and tests

- [x] 1.1 Add RED-first browser-core tests for citation order, citation beyond row 40, supplemental bounds, and missing references.
- [x] 1.2 Add exporter tests that prove synthetic finding IDs resolve to exported evidence.

## Implementation

- [x] 2.1 Export and validate synthetic finding evidence IDs.
- [x] 2.2 Render cited-first evidence cards with distinct citation/supplemental labels in both views.

## Verification

- [x] 3.1 Demonstrate RED then GREEN and run browser/exporter tests.
- [x] 3.2 Run the deterministic suite, strict MkDocs build, and OpenSpec validation.
- [x] 3.3 Verify no citation is truncated and rendering continues to use safe text nodes.
