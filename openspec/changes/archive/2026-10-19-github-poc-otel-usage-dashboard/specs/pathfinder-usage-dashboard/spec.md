# pathfinder-usage-dashboard Specification

## Purpose
Provide a periodically refreshed aggregate view of GitHub Pathfinder PoC usage and outcomes without deploying the Pages application for every analysis run.

## ADDED Requirements
### Requirement: Publish a redacted usage projection independently from Pages deployments

After a Pathfinder job record is appended to `pathfinder-jobs`, the workflow MUST update a versioned aggregate summary on that same branch in the same serialized commit. The summary MUST contain only bounded date-bucketed job counts, allowlisted aggregate analysis statuses and requirement outcome counts, fixed-stage operational metric aggregates (runs, errors, skipped, total duration, maximum duration), generation time, time-window metadata, and model-metering availability. It MUST NOT contain issue/run/job identifiers, repository names, hashes, source/report contents, trace/span identifiers, or personal identifiers. Legacy records without outcome counts, aggregate status, or stage telemetry MUST remain readable.

#### Scenario: Successful record updates summary
- **GIVEN** a valid job record with a report and outcome counts
- **WHEN** the ledger writer commits the record
- **THEN** the same commit contains a regenerated aggregate summary
- **AND** aggregate counts include the job once in the configured reporting window
- **AND** package-level status counts remain distinct from requirement-level outcome counts

#### Scenario: Legacy or invalid ledger lines are encountered
- **GIVEN** old records without outcome counts or malformed JSONL lines
- **WHEN** the projection is generated
- **THEN** supported legacy records contribute only metrics they actually contain
- **AND** unknown aggregate statuses are grouped under a fixed `other` category
- **AND** invalid lines are excluded and counted as bounded projection diagnostics without publishing their contents

#### Scenario: Projection generation fails
- **GIVEN** the new job record is ready to append but projection validation fails
- **WHEN** the writer attempts to publish the ledger update
- **THEN** it does not publish a summary falsely marked fresh
- **AND** the workflow surfaces the failure while preserving already published analysis artifacts/comments

### Requirement: Pages dashboard loads a same-origin protected summary

The Pages application MUST provide a Usage dashboard that fetches a fixed same-origin summary URL from its deployed artifact, validates the schema and all rendered values, and refreshes at most once every five minutes unless manually refreshed. Dashboard fetch/render failure MUST preserve the static Pages site and show an explicit unavailable/stale state. The Pages build MUST embed real summary data only when repository visibility is private and GitHub Pages visibility is private; otherwise it MUST embed a valid empty summary and MUST NOT copy the ledger projection into the artifact.

#### Scenario: Dashboard loads summary from its protected artifact
- **GIVEN** a valid summary is embedded in the private Pages artifact
- **WHEN** the dashboard loads or refreshes
- **THEN** it fetches only the fixed same-origin summary path
- **AND** it displays the summary generation time

#### Scenario: Completed analysis refreshes the Pages artifact
- **GIVEN** a Pathfinder analysis has completed and its serialized ledger job has finished
- **WHEN** the analysis workflow completes
- **THEN** the Pages workflow reuses the persisted site bundle, replaces only the summary JSON, and deploys the refreshed artifact
- **AND** it does not run the full documentation build, Vite build, or site test suite for this data-only refresh
- **AND** it proceeds only when the source run produced the expected evaluation artifact
- **AND** Pages deployments are serialized to avoid overlapping site publications

#### Scenario: Pages or repository visibility is not private
- **GIVEN** the Pages build cannot verify both a private repository and private Pages visibility
- **WHEN** it prepares the dashboard artifact
- **THEN** it embeds a valid empty aggregate snapshot
- **AND** it does not publish data read from the `pathfinder-jobs` branch

#### Scenario: Operator queries stage telemetry by time range and stage
- **GIVEN** the projection contains date-bucketed operational measurements
- **WHEN** the operator selects a supported time window and an optional stage
- **THEN** the dashboard derives counts and duration statistics from only those daily buckets
- **AND** it does not request raw traces or per-run identifiers

#### Scenario: No summary exists yet
- **GIVEN** the `pathfinder-jobs` branch or summary file does not yet exist
- **WHEN** the dashboard loads
- **THEN** it shows a clear no-data-yet state and a link to the Pathfinder workflow
- **AND** it does not treat missing data as zero deviations or successful alignment

#### Scenario: Previous projection exists before the first telemetry-enabled run
- **GIVEN** a valid v1 projection remains on the data branch after the Pages code is updated
- **WHEN** the dashboard loads before a new analysis writes a v2 projection
- **THEN** existing usage and outcome counts remain visible
- **AND** stage telemetry is explicitly marked unavailable until measured records arrive

#### Scenario: Malformed or hostile summary is returned
- **GIVEN** summary JSON has an unsupported schema, invalid counts, unknown outcomes, or hostile text
- **WHEN** the dashboard validates and renders it
- **THEN** it rejects invalid fields, renders no supplied markup/HTML, and reports the snapshot as unavailable

#### Scenario: PoC has no model use
- **GIVEN** the current workflow has not made model calls
- **WHEN** the Usage dashboard displays AI usage
- **THEN** it labels AI usage/spend as not metered for this PoC
- **AND** it does not display misleading zero-token or zero-cost claims

#### Scenario: Private repository mode
- **GIVEN** the repository and GitHub Pages site are private
- **WHEN** the Pages workflow reads the private ledger projection
- **THEN** the build embeds only the aggregate summary in the access-controlled Pages artifact
- **AND** the browser requests no browser-held GitHub token
