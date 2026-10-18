## ADDED Requirements

### Requirement: Evaluate a user-submitted evidence package from a GitHub Issue

When a Pathfinder analyze issue is opened or updated with a valid evidence package, the system MUST pin the package, evaluate it against the approved typed ADR catalog, publish a workflow artifact report, and comment aggregate status plus per-requirement outcomes. The comment MUST NOT paste the full tech-spec or code contents.

#### Scenario: Valid package yields result comment
- **GIVEN** a GitHub issue titled with `[Pathfinder analyze]` containing a valid `pathfinder-evidence-package-v1` JSON block and public/synthetic attestation
- **WHEN** the analyze workflow runs
- **THEN** catalog evaluation executes
- **AND** an issue comment includes aggregate status and outcome counts
- **AND** a workflow artifact contains the full report

#### Scenario: Invalid package fails closed
- **GIVEN** an analyze issue with malformed package JSON or missing attestation
- **WHEN** the analyze workflow runs
- **THEN** evaluation does not invent observations
- **AND** the issue receives an error comment describing the validation failure

#### Scenario: Source is not echoed into the result comment
- **GIVEN** a valid package that includes tech_spec and code content
- **WHEN** the result comment is posted
- **THEN** the comment includes hashes/paths/outcomes
- **AND** the comment does not include the full tech_spec or code body
