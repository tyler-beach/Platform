## ADDED Requirements

### Requirement: Staged GitHub Actions orchestration for analyze

Pathfinder issue analyze MUST run as an ordered chain of stages—intake, ensure-observations, evaluate, publish—implemented with GitHub Actions reusable workflows and/or discrete jobs. Stages MUST exchange durable artifacts (package/report/comment files) rather than embedding full source in workflow expressions. AWS services MUST NOT be required for this capability.

#### Scenario: Happy path completes all stages
- **GIVEN** a Pathfinder analyze issue with a valid package or paste content and attestation
- **WHEN** the orchestrating workflow runs
- **THEN** intake produces a pinned package artifact
- **AND** ensure-observations yields a package with typed observations
- **AND** evaluate produces `report.json`
- **AND** publish posts or updates the issue comment and uploads artifacts

#### Scenario: Intake failure stops before evaluate
- **GIVEN** an analyze issue missing attestation or with malformed structure
- **WHEN** the orchestrating workflow runs
- **THEN** ensure-observations and evaluate do not invent a successful report
- **AND** publish still delivers an error comment when comment publishing is enabled

#### Scenario: Workflow expressions do not carry source bodies
- **GIVEN** any analyze run
- **WHEN** stage outputs and job summaries are inspected
- **THEN** full tech_spec and code bodies are absent from workflow outputs and step summaries
- **AND** content remains only in work-dir / uploaded artifacts under retention policy

### Requirement: Concurrency and comment update semantics

Concurrent analyze runs for the same issue MUST be serialized or cancel-in-progress via an Actions concurrency group keyed by issue number. Publish MUST prefer updating an existing Pathfinder report comment (stable HTML marker) over creating unbounded duplicate comments when the GitHub API permits update.

#### Scenario: Re-run updates prior Pathfinder comment
- **GIVEN** an issue that already has a Pathfinder report comment containing the stable marker
- **WHEN** analyze publish runs successfully again
- **THEN** the existing comment is updated in place when API update succeeds
- **AND** a duplicate Pathfinder report comment is not created

#### Scenario: Concurrent edits do not interleave stages across runs
- **GIVEN** two analyze triggers for the same issue in quick succession
- **WHEN** Actions concurrency is applied
- **THEN** at most one run proceeds to completion for that issue group per concurrency rules
- **AND** cancel-in-progress or queueing prevents mixed artifact handoff from different runs
