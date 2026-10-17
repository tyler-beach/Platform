## Specification and PoC direction

- [x] 1.1 Implement the user-directed shared CSV audit trail for the synthetic PoC.
- [x] 1.2 Use a separate trusted writer with Actions read and repository contents write permissions.
- [x] 1.3 Define the versioned record contract, idempotency key, distinct states, additive schema, serialized writer and reconciliation behavior.
- [x] 1.4 Keep confidence unavailable until validated evidence inputs satisfy the existing algorithm's contract.
- [x] 1.5 Set the PoC recovery scan to 13 days against 14-day final artifact retention; keep retry exhaustion and queue saturation observable.
- [x] 1.6 Enforce default-branch and `workflow_dispatch` ingestion, bounded artifact validation, and unchanged existing CSV headers.

## Implementation

- [x] 2.1 Add regression coverage for schema/hash/identity validation, default-branch and PR exclusion before artifact lookup, idempotency, invalid/oversized archives and source-free Pages projection.
- [x] 2.2 Implement the separate persistence boundary, serialized write workflow, and bounded reconciler.
- [x] 2.3 Add the allowlisted Pages projection behind the existing private/internal visibility gate.
- [x] 2.4 Verify raw source, excerpts, provider payloads, and untrusted artifact fields do not enter the new Pages projection.
- [ ] 2.5 Add isolated tests for API retry exhaustion, Git non-fast-forward exhaustion, queue saturation, and expired-artifact recovery reporting.

## Verification and reconciliation

- [ ] 3.1 Record RED then GREEN for each remaining behavioral scenario.
- [x] 3.2 Run pure-domain tests, workflow contract/security checks, CSV replay tests, Pages projection tests, strict documentation build, and OpenSpec validation.
- [ ] 3.3 Run the writer against a real GitHub Actions artifact in a private PoC repository and inspect the resulting ledger and Pages projection.
- [x] 3.4 Document permissions, retention, rollback, and the fact that deployment has not been performed. Keep this change open until remaining acceptance checks pass.
