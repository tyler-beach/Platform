# Design: Unified Functional Analysis audit record

## Current behavior

`poc-analysis.yml` runs the CSV-backed PoC, writes detailed confidence/evidence data, and persists the CSV snapshot to `poc-database`. `functional-analysis-demo.yml` has read-only repository permissions and passes stage artifacts between jobs, ending with a validated report bundle. `docs.yml` projects bounded Actions job/step metadata and, under an independent opt-in, a redacted CSV ledger projection. The status collector intentionally does not download Actions artifacts.

The new path therefore must not silently be treated as equivalent to the existing ledger path. The end-to-end GitHub Actions run is verified as a deterministic synthetic demonstration, but it has no confidence score and no CSV audit row.

## Proposed record and trust boundary

If ledger integration is approved, add a dedicated versioned CSV table for workflow-run records rather than overloading the existing `runs` or `findings` rows. Preserve all existing CSV headers. Its identity is `(repository, workflow_id, workflow_run_id, run_attempt)`. It references immutable source artifacts by artifact ID and SHA-256 and summarizes validator checks without storing raw input or model-shaped payloads. The record keeps four concepts separate:

- **Execution state:** queued, running, completed, failed, canceled, or timed out, sourced from the Actions run.
- **Analysis state:** not started, incomplete, candidate produced, validated, or rejected.
- **Domain outcome:** a documented analysis result only when the validator accepts it; absent for runs that never produced a valid result.
- **Persistence state:** pending, persisted, duplicate, rejected, or unreconciled, owned by the ledger writer/reconciler.

These are not interchangeable statuses. In particular, a failed validation is a technical/result-validation state and must not be turned into `inconclusive` unless the analysis itself returned that domain outcome.

The Actions artifact is untrusted. A privileged persistence component must first verify the source repository, default-branch policy, workflow identity, successful terminal state, run ID/attempt, artifact name/ID, bounded archive and member sizes, path safety, manifest digests, evidence-to-manifest references, and validation status. It must reject unknown schema versions and never execute or source artifact content.

## Persistence, concurrency, and replay

The existing CSV branch is a PoC persistence adapter, not a transactional database. A dedicated persistence job must serialize the write operation with `poc-analysis.yml`, fetch the latest `poc-database` head before each attempt, verify the CSV schema, apply only the validated record, and use bounded retries for a non-fast-forward conflict. Its idempotency identity is `(repository, workflow_id, workflow_run_id, run_attempt)` and it compares a canonical record fingerprint: same key and same fingerprint is a replay; same key and different fingerprint is a conflict that must not overwrite the original.

Do not use `concurrency` as the delivery queue. Current GitHub Actions semantics allow one pending item per group by default and replace the old pending item with a newer one; the optional larger queue is still bounded. Use queueing only to serialize writes. Add a scheduled and manually recoverable reconciler that scans a bounded recent window of eligible Actions attempts, compares them with ledger identities, and recreates missing execution-only rows or validated analysis rows from a run artifact. The reconciliation horizon must be shorter than the minimum artifact retention period; the current final bundle retention is 14 days, so the proposal is a 13-day scan with an explicit alert for any older missing result. If an artifact is expired, record the run as unreconciled with no domain outcome rather than claiming a complete audit.

The reconciliation operation itself must be idempotent, bounded by page/run/artifact limits, and safe to rerun. It should report scanned, persisted, replayed, rejected, and unrecoverable counts in a job summary. It must never report complete reconciliation when any eligible attempt remains missing or rejected. GitHub currently limits `queue: max` to 100 pending runs; this is a throughput guard, not durable intent storage. A run older than the configured scan horizon is surfaced as unreconciled rather than silently dropped. A successful run initially recorded as unreconciled must be retried while it remains in the automatic recovery window, because an artifact can become visible after the workflow completion event. The summary must also count the latest unresolved ledger revisions outside that window so a bounded scan cannot report green while old failures remain.

Use a separate `workflow_run`-triggered writer defined on the default branch as the preferred design to keep write permission out of the workflow that analyzes source-derived content. Before querying or downloading artifacts, the writer must verify through the Actions API that the source run belongs to the same repository, is the approved workflow ID and `workflow_dispatch` event, and has `head_branch` equal to the repository's current default branch. Only successful eligible runs may contribute a validated analysis result. Runs from pull requests or non-default branches remain available as Actions history and run-scoped artifacts; they do not enter the shared ledger. The scheduled reconciler may write execution-only metadata for eligible default-branch attempts that failed or were canceled, but it must not infer analysis results from them.

The writer still treats downloaded artifacts as hostile data. It must verify the approved workflow ID and source workflow SHA, event type, repository, default-branch name, run ID/attempt, exact artifact ID/name, artifact size and digest where provided. Before extraction it must bound compressed and expanded bytes, member count, path depth and individual file sizes; reject absolute paths, `..`, symlinks, duplicate names, unknown files, and unsupported schemas; then validate manifest hashes and evidence references. It must not execute, source, or interpolate any artifact path or string into a shell command. It must use only the permissions needed to read Actions metadata/artifacts and update the ledger branch. Pull-request-originated and non-default-branch runs must be rejected before artifact lookup/download. This is a recommendation for review, not an accepted decision.

The alternative is a final job in `functional-analysis-demo.yml` with `contents: write`. That is simpler but gives the same workflow that processes source-derived content the authority to mutate a repository branch; it also makes manual runs from a non-default ref part of the trust boundary.

The persisted row schema is additive (for example, `workflow_run_records.csv`) and versioned. Existing `runs.csv`, `findings.csv`, confidence tables, and their headers remain unchanged. The CSV writer enforces uniqueness by scanning the composite identity under the serialized write operation; append-only CSV itself does not provide a database uniqueness constraint. The job summary and scheduled reconciler provide the operational signal when persistence is rejected, queued past the recoverable window, or cannot be repaired.

## Confidence policy

The fixture oracle is only an acceptance test. It cannot feed a confidence score. The existing evidence-strength algorithm expects validated requirements, observations, explicit evidence links, source provenance, and coverage data. Compute that score only if the Functional Analysis pipeline supplies the same validated inputs and contract. Otherwise record confidence as unavailable and explain which inputs are missing. Any later scoring change requires labeled evaluation evidence and before/after reporting.

## Pages projection

The static Pages document may show a bounded allowlist of record fields and a run link constructed from the configured repository plus numeric run ID. It must use the existing organization/private-or-internal/private-Pages gates. It must not fetch or embed raw workflow bundles, source files, or provider payloads. Run/job status metadata remains independently controllable from detailed ledger export. The UI must label execution-only, incomplete, rejected, and validated records accurately and show when data is unreconciled or stale.

## Alternatives

- Keep separate artifacts and ledger workflows: least privilege and lowest integration cost, but no unified durable audit row for Functional Analysis.
- Let the Functional Analysis workflow write the CSV branch directly: fewer handoff components, but increases permissions on a workflow that processes source-derived content.
- Add a separate artifact-consuming writer and scheduled reconciler: clearer trust separation and recoverability, but requires a carefully validated cross-workflow artifact boundary and expiry handling.

No alternative is accepted until the primary decision and write-authority choice are reviewed.

## External behavior references

- GitHub Actions concurrency only keeps one pending run by default; additional pending work replaces the old pending run. The optional queue supports up to 100 pending runs: [GitHub concurrency documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).
- A `workflow_run` workflow can access secrets and write-capable tokens even when the triggering workflow cannot; GitHub warns to treat downloaded artifacts as untrusted and not execute them: [workflow_run event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), [secure use reference](https://docs.github.com/en/actions/reference/security/secure-use).
