## Specification and test-first

- [x] 1.1 Define the generated scenario matrix, fixture boundary, source pane behavior, and offline availability.
- [x] 1.2 Add regression tests for catalog completeness, live artifact provenance/validation, fixture path/hash safety, and browser rendering behavior; demonstrate RED before implementation.

## Implementation

- [x] 2.1 Build all nine scenarios from the deterministic Functional Analysis pipeline into a bounded, versioned static JSON catalog.
- [x] 2.2 Import and validate up to ten recent eligible Functional Analysis run artifacts, projecting their synthetic inputs and allowlisted outputs into the gallery.
- [x] 2.3 Add a responsive Pages scenario selector and side-by-side synthetic ADR/spec/source/diff panes with provenance and selected analysis outputs.
- [x] 2.4 Wire generation and catalog validation into the docs workflow without depending on CSV ledger opt-ins.
- [x] 2.5 Update the demo guide to distinguish curated synthetic scenarios from actual recent workflow attempts.

## Verification

- [x] 3.1 Run gallery generator and Python behavior/security tests; verify all nine curated outputs and synthetic live-bundle validation.
- [x] 3.2 Run browser-core tests for scenario selection, safe text rendering, provenance, malformed catalog rejection, and mobile/accessible structure.
- [x] 3.3 Run strict MkDocs build and OpenSpec validation; report checks not run.
