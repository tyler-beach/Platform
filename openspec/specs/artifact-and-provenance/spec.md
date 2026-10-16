# Artifact and provenance

## Purpose
Maintain source-backed artifacts and immutable versions so findings point to the exact information used in assessment.

## Requirements

### Requirement: Artifacts have immutable versions
The system MUST represent a logical artifact separately from each imported or observed source version.

#### Scenario: New source version arrives
- GIVEN an artifact already exists
- WHEN a new document version or repository commit is ingested
- THEN the system creates or resolves a distinct artifact version with source identity and content hash
- AND prior versions remain addressable for earlier analysis results.

#### Scenario: Duplicate version arrives
- GIVEN an artifact version with the same authoritative identity and content hash exists
- WHEN the same version is ingested again
- THEN ingestion recognizes the existing version
- AND does not create duplicate active records merely because delivery was repeated.

### Requirement: Evidence is version-bound
Every persisted finding MUST cite references that resolve to a specific artifact version and location.

#### Scenario: Finding is inspected
- GIVEN a validated finding
- WHEN a reviewer opens its evidence
- THEN each reference resolves to the source version and location used by the job
- AND any difference from current source is explicit.

#### Scenario: Source changes after analysis
- GIVEN a job used version A and version B becomes current
- WHEN the result is read or published
- THEN the finding remains linked to A
- AND publication can check freshness before commenting on B.

### Requirement: Derived indexes are not authoritative
The system MUST treat embeddings, summaries, full-text indexes and extracted interpretations as derived data linked to source versions.

#### Scenario: Source version updates
- GIVEN derived data was built from version A
- WHEN version B is ingested
- THEN stale derived data is detectable and reindexing can be scheduled
- AND historical provenance remains intact.

### Requirement: Decision lifecycle is represented
The system MUST track or resolve decision status, scope and supersession before treating a decision as governing policy.

#### Scenario: Superseded ADR is retrieved
- GIVEN decision A was superseded by decision B
- WHEN applicable decisions are resolved
- THEN A is not silently applied as a current mandate
- AND any historical use is explicit.
