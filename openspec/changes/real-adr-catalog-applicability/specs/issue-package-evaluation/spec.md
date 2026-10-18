## MODIFIED Requirements

### Requirement: Evaluate a user-submitted evidence package from a GitHub Issue

When a Pathfinder analyze issue is opened or updated with a valid evidence package, extractable paste content, **or a same-repo PR adapter package**, the system MUST pin the package, ensure typed observations, apply ADR applicability filtering, evaluate in-scope requirements against the configured typed ADR catalog using the Go Pathfinder runtime, publish a workflow artifact report that names the catalog identity, comment aggregate status plus per-requirement outcomes via staged GitHub Actions orchestration, and attempt a job-ledger append. The comment MUST NOT paste the full tech-spec or code contents. Findings remain advisory. The production workflow MUST NOT invoke Python `.poc/issue_analyze/issue_package.py` or `.poc/requirement_engine/evaluate_package.py` as the evaluate entrypoint.

#### Scenario: Valid package yields result comment
- **GIVEN** a GitHub issue titled with `[Pathfinder analyze]` containing a valid `pathfinder-evidence-package-v1` JSON block and public/synthetic attestation
- **WHEN** the analyze workflow runs
- **THEN** Go catalog evaluation executes through staged Actions jobs or reusable workflows
- **AND** an issue comment includes aggregate status and outcome counts
- **AND** a workflow artifact contains the full report

#### Scenario: Invalid package fails closed
- **GIVEN** an analyze issue with malformed package JSON or missing attestation
- **WHEN** the analyze workflow runs
- **THEN** evaluation does not invent observations
- **AND** the issue receives an error comment describing the validation failure

#### Scenario: Source is not echoed into the result comment
- **GIVEN** a valid package that includes tech_spec or code content
- **WHEN** the result comment is posted
- **THEN** the comment includes hashes/paths/outcomes
- **AND** the comment does not include the full tech_spec or code body

#### Scenario: Production entrypoint is Go not Python
- **GIVEN** the Pathfinder issue analyze workflow definition on the default branch
- **WHEN** the evaluate/publish path is inspected
- **THEN** the production steps invoke the Go `pathfinder-issue-analyze` binary (or stage-specific Go commands built from `go/pathfinder`)
- **AND** they do not call `python .poc/issue_analyze/issue_package.py` for production evaluation

#### Scenario: Same-repo PR input evaluates
- **GIVEN** an analyze issue with attestation and a same-repo PR reference that resolves within caps
- **WHEN** the analyze workflow runs
- **THEN** intake produces a pinned package from the PR head changed files
- **AND** evaluation comment and report artifacts are published

#### Scenario: Report identifies catalog identity
- **GIVEN** a successful Pathfinder analyze evaluation
- **WHEN** the report and issue comment are produced
- **THEN** catalog identity (mode and version/hash) is present on the report
- **AND** the comment surfaces enough catalog identity for a reader to know which pack was used
