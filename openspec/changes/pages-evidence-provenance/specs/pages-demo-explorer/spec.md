## MODIFIED Requirements

### Requirement: Publish bounded synthetic and internal run records
The documentation build MUST generate an in-page walkthrough from the checked-in fixture and mock provider. It MAY additionally publish bounded real run records only when repository visibility is `private`, the GitHub Pages API reports `public: false`, and `PAGES_REAL_RUN_DATA_ENABLED` is exactly `true`. The real-data step MUST NOT run for pull-request events. Internal Pages run links and API requests MUST use the cloned repository identity. It MUST include only allowlisted summary, stage, evidence, observation/coverage, confidence, and finding fields. It MUST NOT publish credentials, prompts, provider request/response payloads, or raw workflow artifacts. Every projected evidence and observation reference MUST resolve by artifact ID to a unique artifact row in the same run, and its path and full SHA-256 MUST match that artifact row. Stored evidence excerpt hashes MUST match the stored excerpt before redaction. Every non-inconclusive finding MUST resolve at least one cited evidence ID to an evidence record included in the projection. Invalid or ambiguous references MUST fail the projection.

#### Scenario: Internal evidence has exact artifact provenance
- **GIVEN** an internal run contains evidence and observations linked to versioned source artifacts
- **WHEN** the Pages exporter projects the run
- **THEN** each reference is checked by artifact ID, path, and full SHA-256 against the same run's artifact row
- **AND** the projected record retains the exact artifact digest and source locator

#### Scenario: Internal evidence has missing or mismatched provenance
- **GIVEN** an evidence or observation row has a missing artifact, an ambiguous artifact ID, a mismatched path, or a mismatched/invalid source digest
- **WHEN** the Pages exporter projects the run
- **THEN** the projection fails before the Pages artifact is uploaded
- **AND** the reference is not displayed as source-version verified

#### Scenario: Finding cites absent or unpinned evidence
- **GIVEN** an internal finding has a conclusive outcome but no evidence IDs, or cites an ID absent from the same run's projected evidence
- **WHEN** the Pages exporter projects the run
- **THEN** the projection fails before the Pages artifact is uploaded
- **AND** the finding is not displayed without resolvable source-version evidence
