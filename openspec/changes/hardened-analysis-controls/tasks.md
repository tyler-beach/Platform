## Contract and implementation

- [ ] 1.1 Review and approve the proposed dispatch, replay and cumulative-budget requirements.
- [ ] 1.2 Select the durable dispatch mechanism and document failure-recovery state transitions.
- [ ] 1.3 Implement transactional job/idempotency/dispatch-intent persistence.
- [ ] 1.4 Implement dispatcher claim/lease, start, compare-and-set update and stale-intent reconciliation.
- [ ] 1.5 Add per-effect idempotency keys and uniqueness constraints for jobs, findings and publication.
- [ ] 1.6 Define cancellation/fencing behavior when cancellation races with persistence or publication.
- [ ] 1.7 Implement durable model-budget reservation/ledger with concurrency-safe accounting.
- [ ] 1.8 Add per-operation input/output and per-job cumulative token/spend/call/retry/deadline limits.
- [ ] 1.9 Reconcile estimated usage, provider usage, effective-dated price version and ambiguous failed-attempt charges.
- [ ] 1.10 Add deterministic compaction with required/counter-evidence preservation and omitted-evidence records.

## Tests and operations

- [ ] 2.1 Add RED-first unit tests for budget boundaries, state transitions, evidence validation and canonical request fingerprints.
- [ ] 2.2 Add property/fuzz tests for stable ordering, evidence locator bounds, parsing and hashes.
- [ ] 2.3 Fault-inject crashes before/after database commit and before/after workflow start; prove reconciliation.
- [ ] 2.4 Test duplicate webhook, duplicate worker, lost response, retry exhaustion and publication replay.
- [ ] 2.5 Test concurrent budget reservations, retries, timeout after possible provider acceptance and optional verifier denial.
- [ ] 2.6 Add authorization/prompt-injection/redaction tests across tenant and source boundaries.
- [ ] 2.7 Add/expand labeled AI evaluation corpus; report before/after outcome, evidence-validity, abstention, cost and latency.
- [ ] 2.8 Add metrics/alerts/runbooks for stuck dispatch, budget exhaustion, spend drift, validation spikes and replay.
- [ ] 2.9 Run required tests and record actual results; do not mark unrun checks complete.
- [ ] 2.10 Update current-state specs and archive only after review and acceptance evidence pass.
