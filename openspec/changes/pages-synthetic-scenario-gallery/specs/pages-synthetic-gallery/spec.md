## ADDED Requirements

### Requirement: Publish an offline synthetic scenario gallery

The Pages build MUST generate a versioned static scenario catalog from the approved synthetic Functional Analysis fixtures. The catalog MUST cover `code-diff`, `technical-spec`, and `spec-vs-implementation` comparisons for `deviation`, `aligned`, and `insufficient-evidence` cases. Each curated scenario MUST pass the deterministic workflow's evidence and result validation before publication.

The Pages build MAY add up to ten recent successful Functional Analysis Demo artifacts when they originate from the same repository's approved workflow ID, a `workflow_dispatch` event, and the repository default branch, and were created within the 13-day recovery horizon. Before artifact lookup/download it MUST verify run identity, workflow identity, event, branch, conclusion, attempt, exact expected artifact name and artifact run ID. It MUST validate the artifact digest, bundle bounds, manifest identity, input hashes, evidence references, and deterministic mock result using the existing ledger bundle validator. For live entries it MUST accept only input paths matching the selected comparison, sample case, and language under `.github/demo/fixtures`; it MUST publish only validated input text and allowlisted analysis/evidence/check metadata. It MUST never execute artifact content or include prompts, credentials, or arbitrary bundle members. Invalid, expired, or ineligible artifacts MUST be excluded and counted in bounded build metadata.

The gallery MUST NOT read ledger rows or files outside the approved synthetic fixture tree. Its curated scenarios MUST remain available when live Actions history and detailed ledger exports are disabled.

#### Scenario: Build the complete synthetic comparison matrix
- **GIVEN** the approved synthetic fixture tree and deterministic mock workflow are available
- **WHEN** the documentation build generates the scenario catalog
- **THEN** it publishes all nine comparison/sample combinations with their validated outcome and stage summaries
- **AND** every input is tied to its exact fixture path and SHA-256 digest
- **AND** a failed analysis or validation prevents catalog generation from succeeding.

#### Scenario: Include a recent synthetic workflow artifact
- **GIVEN** a successful `workflow_dispatch` run of the approved Functional Analysis workflow on the default branch within the recovery horizon
- **AND** its final artifact matches the expected run/attempt identity, Actions digest, synthetic fixture paths, and validated bundle contract
- **WHEN** the Pages gallery is generated
- **THEN** the actual workflow input files and allowlisted validated output are added as a distinct run-attempt entry
- **AND** the entry includes its source workflow SHA, run/attempt link, artifact digest, input hashes, and validation checks.

#### Scenario: Exclude an untrusted or unrecoverable workflow artifact
- **GIVEN** an artifact comes from a pull request, another workflow, a non-default branch, a failed run, an expired bundle, an unexpected fixture path, or a mismatched digest or run identity
- **WHEN** the Pages importer evaluates it
- **THEN** it does not publish the artifact contents
- **AND** it increments a bounded exclusion count without treating the artifact as a valid analysis result.

#### Scenario: Reject an input outside the approved fixture tree
- **GIVEN** catalog generation receives an artifact path that resolves outside `.github/demo/fixtures`
- **WHEN** the generator validates the scenario inputs
- **THEN** it fails before publishing the catalog
- **AND** it does not copy or serialize the out-of-tree file.

### Requirement: Explore scenario inputs and outputs on Pages

The demo page MUST let a visitor select a catalog scenario and inspect the exact synthetic ADR, technical specification, implementation, and diff inputs that apply to that comparison. Each input pane MUST show the path and SHA-256 digest. The page MUST show the scenario outcome, evidence references, deterministic stage summaries, and validation checks. Source text MUST be inserted as text, never interpreted as HTML or script. Layout MUST remain usable on narrow screens and MUST expose scenario selection and status to assistive technology.

#### Scenario: Compare the specification with implementation
- **GIVEN** a `spec-vs-implementation` scenario is selected
- **WHEN** the gallery renders its inputs
- **THEN** the technical specification and implementation appear in adjacent panes
- **AND** the ADR and diff remain available as additional source panes
- **AND** source path and SHA-256 provenance are visible for each pane.

#### Scenario: Browse an ADR-to-code scenario
- **GIVEN** a `code-diff` scenario is selected
- **WHEN** the gallery renders its inputs
- **THEN** the ADR, implementation, and diff appear with the validated outcome and evidence links
- **AND** the UI does not imply that a technical specification was part of that comparison.

#### Scenario: Display adversarial fixture text safely
- **GIVEN** a synthetic fixture contains HTML-like text
- **WHEN** the visitor selects its scenario
- **THEN** the text is shown literally in the source pane
- **AND** no fixture content executes as markup or script.

#### Scenario: Browse without live history access
- **GIVEN** Actions history and detailed ledger export are disabled or unavailable
- **WHEN** the demo page loads its same-origin static catalog
- **THEN** the visitor can still select and inspect every generated synthetic scenario.
- **AND** absence of live workflow artifacts does not remove the curated fixture scenarios.
