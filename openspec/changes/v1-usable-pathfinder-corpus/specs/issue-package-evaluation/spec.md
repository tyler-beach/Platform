## MODIFIED Requirements

### Requirement: Evaluate a user-submitted evidence package from a GitHub Issue

When a Pathfinder analyze issue is opened or updated with a valid evidence package, extractable paste content, **or a same-repo PR adapter package**, the system MUST pin the package, ensure typed observations, apply ADR applicability filtering, evaluate in-scope requirements against the configured typed ADR catalog using the Go Pathfinder runtime (defaulting to the real prototype pack unless synthetic is explicitly selected), publish a workflow artifact report that names the catalog identity, comment aggregate status plus per-requirement outcomes and coverage guidance via staged GitHub Actions orchestration, and attempt a job-ledger append. The comment MUST NOT paste the full tech-spec or code contents. Findings remain advisory. The production workflow MUST NOT invoke Python `.poc/issue_analyze/issue_package.py` or `.poc/requirement_engine/evaluate_package.py` as the evaluate entrypoint.

#### Scenario: Valid package yields result comment
- **GIVEN** a GitHub issue titled with `[Pathfinder analyze]` containing a valid `pathfinder-evidence-package-v1` JSON block and public/synthetic attestation
- **WHEN** the analyze workflow runs
- **THEN** Go catalog evaluation executes through staged Actions jobs or reusable workflows
- **AND** an issue comment includes aggregate status and outcome counts
- **AND** a workflow artifact contains the full report

#### Scenario: Comment includes coverage guidance
- **GIVEN** a successful Pathfinder analyze evaluation
- **WHEN** the result comment is posted
- **THEN** the comment includes catalog identity and in-scope requirement count
- **AND** the comment explains that unextracted predicates remain `inconclusive`

#### Scenario: Explicit synthetic catalog selection
- **GIVEN** an analyze issue or workflow input that selects catalog mode `synthetic`
- **WHEN** evaluation runs
- **THEN** the report catalog mode is `synthetic`
