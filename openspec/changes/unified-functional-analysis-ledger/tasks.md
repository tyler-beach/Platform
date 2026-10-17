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
- [x] 2.5 Add isolated tests for API retry exhaustion, Git non-fast-forward exhaustion, bounded scan saturation, and expired-artifact recovery reporting.
- [x] 2.6 Retry unresolved ledger identities during scheduled reconciliation and test recovery when the final artifact becomes available later.
- [x] 2.7 Keep unresolved ledger rows visible as incomplete after they age out of the automatic recovery scan.
- [x] 2.8 Make the scheduled reconciler directly executable from the repository root without ambient `PYTHONPATH`, with subprocess regression coverage.
- [x] 2.9 Normalize the repository metadata request URL and cover it with an API adapter regression test.

## Verification and reconciliation

- [ ] 3.1 Record RED then GREEN for each remaining behavioral scenario. The oversized-history, artifact-lag recovery, and out-of-window reporting cases were observed RED and are now GREEN. Retry exhaustion and expired-artifact behavior were already green at baseline. Keep this task open until the hosted concurrency queue overflow/recovery path is demonstrated in the private PoC repository.
- [x] 3.2 Run pure-domain tests, workflow contract/security checks, CSV replay tests, Pages projection tests, strict documentation build, and OpenSpec validation.
- [ ] 3.3 Run the writer against a real GitHub Actions artifact in a private PoC repository and inspect the resulting ledger and Pages projection.
- [x] 3.4 Document permissions, retention, rollback, and deployment status. GitHub Pages was deployed successfully with synthetic history; the real writer against an Actions artifact has not been run. Keep this change open until remaining acceptance checks pass.
