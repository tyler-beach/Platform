# pathfinder-usage-dashboard Specification

## Purpose
Provide an aggregate usage and alignment dashboard on the static GitHub Pages site, refreshed by deploying a persisted static bundle with updated aggregate JSON after each completed analysis workflow.

## Requirements
### Requirement: Publish a redacted usage projection independently from Pages deployments

After a Pathfinder job record is appended to `pathfinder-jobs`, the serialized workflow MUST update the versioned `dashboard/summary.json` projection on that same branch in the same commit. The projection MUST contain bounded date-bucketed job counts, allowlisted aggregate analysis statuses and requirement outcomes, fixed-stage operational aggregates (runs, errors, skipped, total duration, and maximum duration), generation time, window metadata, record diagnostics, and model-metering availability. It MUST NOT contain issue/run/job identifiers, repository names, hashes, source/report contents, trace/span identifiers, or personal identifiers. Supported legacy records MUST remain readable.

#### Scenario: Successful record updates the projection
- **GIVEN** a valid job record with aggregate status and finding counts
- **WHEN** the ledger writer commits the record
- **THEN** the same commit contains an updated projection
- **AND** package-level statuses remain distinct from per-requirement outcomes

#### Scenario: Legacy and malformed records occur
- **GIVEN** supported v1 records or malformed JSONL lines
- **WHEN** the projection is generated
- **THEN** only available fields from legacy records contribute
- **AND** malformed records are excluded and counted without publishing their contents
- **AND** unknown aggregate statuses are placed in a fixed `other` bucket

### Requirement: Pages dashboard loads a protected same-origin summary

The Pages application MUST provide a Usage route that fetches only a fixed same-origin summary path from its deployed artifact, validates the versioned schema and rendered values, and refreshes at most every five minutes unless manually requested. The UI MUST show the generated timestamp and unavailable/stale states. Failure to fetch or validate the snapshot MUST NOT prevent the static site from loading. Pages builds MUST include real aggregate data only when both the repository and Pages site are verified private; otherwise they MUST include a valid empty summary.

#### Scenario: New projection is available
- **GIVEN** a newer projection is committed to the data branch
- **WHEN** the completed analysis triggers a Pages deployment
- **THEN** the site artifact contains that summary at its same-origin data path
- **AND** the data-only deployment reuses the persisted site bundle without rerunning the full site build or tests
- **AND** the UI shows its generation time

#### Scenario: Analysis completion updates private Pages
- **GIVEN** a Pathfinder analysis workflow has completed its serialized ledger job
- **WHEN** the data refresh workflow runs
- **THEN** it serializes Pages publication with other site updates
- **AND** it replaces only the aggregate JSON in the persisted bundle
- **AND** it refreshes only when the source run produced the expected evaluation artifact
- **AND** a verified private Pages site receives the latest bounded aggregate
- **AND** an unverified or public site receives only an empty summary

#### Scenario: Operator filters operational aggregates
- **GIVEN** daily stage metrics are present in the validated projection
- **WHEN** the operator selects a supported date window and stage
- **THEN** the UI computes the matching runs/errors/skips and duration statistics from those buckets

#### Scenario: Snapshot is absent, stale, or invalid
- **GIVEN** the data branch/file is missing, stale, or returns hostile fields
- **WHEN** the dashboard loads or refreshes
- **THEN** it preserves any last good snapshot, shows a clear state, and renders no supplied markup
- **AND** it does not invent zero deviation or successful alignment

#### Scenario: Previous projection remains until the next ledger write
- **GIVEN** a valid v1 aggregate still exists after the Pages bundle is updated
- **WHEN** the dashboard loads before any v2 projection is generated
- **THEN** it continues to show the prior usage counts
- **AND** it labels new operational telemetry unavailable rather than recording zero measurements

#### Scenario: Public Pages cannot receive private aggregate data
- **GIVEN** the repository or Pages visibility is public or cannot be verified
- **WHEN** a Pages deployment is built
- **THEN** the artifact contains a valid empty summary
- **AND** no ledger summary is copied into the public artifact

#### Scenario: AI metering is unavailable
- **GIVEN** the current workflow performs no model calls
- **WHEN** AI usage is shown
- **THEN** the dashboard says usage and spend are not metered, not zero
