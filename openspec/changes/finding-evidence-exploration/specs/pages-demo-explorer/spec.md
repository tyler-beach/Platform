## MODIFIED Requirements

### Requirement: Publish bounded synthetic and internal run records
The documentation build MUST generate an in-page walkthrough from the checked-in fixture and mock provider. It MAY additionally publish bounded real run records only when repository visibility is `private`, the GitHub Pages API reports `public: false`, and `PAGES_REAL_RUN_DATA_ENABLED` is exactly `true`. The real-data step MUST NOT run for pull-request events. Internal Pages run links and API requests MUST use the cloned repository identity. It MUST include only allowlisted summary, stage, evidence, observation/coverage, confidence, and finding fields. It MUST NOT publish credentials, prompts, provider request/response payloads, or raw workflow artifacts. Evidence IDs cited by a finding MUST be included in the projection and shown in the explorer before supplemental evidence. All cited evidence MUST be displayed, including citations beyond the supplemental display limit; supplemental evidence MAY be capped at 40 items. The synthetic walkthrough MUST apply the same citation behavior.

#### Scenario: Finding evidence is explored
- **GIVEN** a run projection contains a finding with evidence IDs and matching evidence records
- **WHEN** the visitor expands the run record or synthetic walkthrough
- **THEN** all cited evidence appears first and is labelled as a finding citation
- **AND** uncited records are labelled as additional evidence and capped at 40
- **AND** each card shows its evidence ID and source-version digest

#### Scenario: Finding refers to evidence absent from the snapshot
- **GIVEN** a finding cites an evidence ID not present in its projection
- **WHEN** the explorer prepares the evidence list
- **THEN** it reports a visible integrity error
- **AND** it does not silently show an incomplete list as the full evidence trail
