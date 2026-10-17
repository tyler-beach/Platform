## Specification and tests

- [x] 1.1 Add RED-first tests for independent exact opt-ins and shared fail-closed visibility checks.
- [x] 1.2 Add workflow contract tests proving history-only mode avoids ledger clone and ledger-only mode skips Actions API collection.

## Implementation

- [x] 2.1 Add a Pages visibility guard for the Actions-history opt-in.
- [x] 2.2 Refactor the docs export step to gate Actions history and CSV ledger independently.
- [x] 2.3 Update the runbook with the two flags and their separate effects.

## Verification

- [x] 3.1 Demonstrate RED then GREEN for the new visibility guard and runbook contract; verify the history-only projection contains Actions metadata and zero ledger records.
- [x] 3.2 Run exporter/unit tests (63 deterministic tests), strict MkDocs build, browser tests (11), workflow shell syntax validation, and OpenSpec validation.
- [x] 3.3 Verify history-only projection contains no ledger rows or source/artifact payloads and neither flag exports on PR builds.
