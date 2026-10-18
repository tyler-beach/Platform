# pathfinder-job-ledger Specification

## Purpose
Append-only lean job index on the `pathfinder-jobs` branch for Pathfinder analyze runs, without storing full source or full report bodies.
## Requirements
### Requirement: Append lean job records to pathfinder-jobs

After a Pathfinder analyze evaluation completes (success or validated failure with report/comment artifacts), the system MUST attempt to append one lean JSON line to an append-only ledger file on the `pathfinder-jobs` git branch. Each record MUST include `job_id`, issue number, GitHub `run_id` and `run_attempt`, package and report fingerprints when available, aggregate status (or error class), timestamps, and engine version. The record MUST NOT embed full tech_spec/code bodies or the full report JSON; those remain in workflow artifacts.

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

