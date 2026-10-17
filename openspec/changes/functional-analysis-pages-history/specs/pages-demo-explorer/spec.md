## ADDED Requirements

### Requirement: Show bounded history for the functional analysis workflow
The internal Pages run explorer MUST include bounded run, job, and step status metadata for the Functional Analysis Demo workflow. The documentation refresh MUST accept completed default-branch runs of that workflow and MUST exclude pull-request executions. The projection MUST construct run links from the configured repository identity and validated numeric run IDs. Workflow launch links on both the explorer and guide page MUST use the checked-out repository identity. It MUST NOT fetch or publish workflow artifacts, source files, prompts, credentials, or raw API responses through the history collector. The existing real-data visibility gate and synthetic walkthrough behavior MUST remain unchanged.

#### Scenario: Default-branch Functional Analysis Demo completes
- **GIVEN** the Functional Analysis Demo completes from the default branch
- **WHEN** the documentation workflow refreshes the Pages artifact
- **THEN** the bounded run, job, and step status metadata appears in the internal Actions history
- **AND** run links use the checked-out repository identity
- **AND** no workflow artifact or source payload is downloaded or included

#### Scenario: Functional Analysis Demo is run from a pull request
- **GIVEN** the Functional Analysis Demo completes for a pull-request event
- **WHEN** the documentation workflow evaluates its workflow-run trigger
- **THEN** it does not refresh or publish a Pages artifact from that run

#### Scenario: Real-data export is not enabled
- **GIVEN** the Pages real-data opt-in is absent or false
- **WHEN** the documentation site is built after a Functional Analysis Demo run
- **THEN** the synthetic walkthrough is generated
- **AND** the real CSV ledger export remains disabled
