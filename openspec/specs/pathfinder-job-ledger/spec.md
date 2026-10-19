# pathfinder-job-ledger Specification

## Purpose
Append-only lean job index on the `pathfinder-jobs` branch for Pathfinder analyze runs, without storing full source or full report bodies.
## Requirements
### Requirement: Append lean job records to pathfinder-jobs

After a Pathfinder analyze evaluation completes (success or validated failure with report/comment artifacts), the system MUST attempt to append one lean JSON line to an append-only ledger file on the `pathfinder-jobs` git branch. Each record MUST include `job_id`, issue number, GitHub `run_id` and `run_attempt`, package and report fingerprints when available, aggregate status (or error class), timestamps, and engine version. The record MUST NOT embed full tech_spec/code bodies or the full report JSON; those remain in workflow artifacts. The current v3 record MAY include allowlisted non-negative counts for `supported_deviation`, `no_deviation_found`, `inconclusive`, and `not_applicable`, and fixed-key stage telemetry aggregates (runs, errors, skipped, total duration, maximum duration). Stage telemetry MUST NOT include trace/span IDs, dynamic identifiers, content, or error messages. Readers MUST continue to accept v1/v2 records.

#### Scenario: Successful evaluate appends ledger line
- **GIVEN** a Go analyze run that produced `report.json` and `comment.md`
- **WHEN** the ledger stage runs
- **THEN** a new JSON line is committed on `pathfinder-jobs` containing job identity, fingerprints, and aggregate status
- **AND** the line does not include full source bodies

#### Scenario: Ledger writes are serialized and retried
- **GIVEN** concurrent analyze runs finishing near-once
- **WHEN** ledger commits race
- **THEN** writes are serialized via an Actions concurrency group for the ledger
- **AND** a rejected push is retried with fetch→append→commit within a bounded attempt count

### Requirement: Ledger failure must not erase user-visible results

When evaluation and comment publish succeed but the ledger commit fails after retries, the workflow MUST still retain the issue comment and evaluation artifacts, and MUST surface the ledger failure as a soft failure or warning rather than deleting the comment.

#### Scenario: Comment kept when ledger fails
- **GIVEN** a successful evaluate and comment update
- **AND** the `pathfinder-jobs` commit fails after bounded retries
- **WHEN** the workflow finishes
- **THEN** the Pathfinder comment remains on the issue
- **AND** evaluation artifacts remain downloadable
- **AND** the run is marked failed or warned for the ledger step without rolling back the comment

### Requirement: Publish a bounded usage projection with each ledger append

The serialized ledger workflow MUST regenerate `dashboard/summary.json` from supported v1/v2/v3 records and commit it with the JSONL append. The projection MUST contain no issue/run/job identifiers, repository names, hashes, source/report contents, trace/span identifiers, or personal identifiers. It MUST include bounded daily job counts, allowlisted aggregate statuses and requirement outcomes, fixed-stage telemetry aggregates, freshness/window metadata, and model-metering state. Legacy records MUST remain readable; unknown aggregate statuses MUST map to `other`.

#### Scenario: Successful record refreshes the projection
- **GIVEN** a valid job record is appended within the 90-day reporting window
- **WHEN** the serialized ledger writer commits
- **THEN** that same commit contains the updated projection and ledger line
- **AND** one job contributes once to job totals and its allowlisted result counts

#### Scenario: Old or malformed records are encountered
- **GIVEN** supported v1 records or malformed JSONL records
- **WHEN** the projection is generated
- **THEN** v1 records contribute only fields they contain
- **AND** malformed records are excluded and counted without echoing their contents

