## Specification and tests

- [x] 1.1 Add RED-first coverage proving the Functional Analysis Demo workflow is included in bounded run history and source/artifact fields are excluded.
- [x] 1.2 Add a contract check that the docs workflow refreshes on this workflow and retains pull-request exclusion.

## Implementation

- [x] 2.1 Add the workflow to the Actions-history allowlist.
- [x] 2.2 Add the completed workflow trigger and path filters needed to keep docs checks current.
- [x] 2.3 Update the demo site documentation to explain the history link.

## Verification

- [x] 3.1 Demonstrate RED then GREEN for the focused behavior tests; the workflow collector, browser link, and cloned-repository link tests failed before their corresponding implementation and passed afterward.
- [x] 3.2 Run deterministic demo tests, OpenSpec validation, and strict MkDocs build.
- [x] 3.3 Inspect the generated history projection for source/artifact payload exclusion; the fake API response included source and artifact canaries, and the projected JSON omitted them without requesting artifact endpoints.
