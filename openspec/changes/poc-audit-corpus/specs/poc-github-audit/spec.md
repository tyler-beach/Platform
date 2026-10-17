# PoC GitHub audit workflow

## ADDED Requirements

### Requirement: Configuration-only analyses use the existing workflow entry point
The manual GitHub Actions analysis workflow MUST support configuration evidence collection without selecting a programming language.

#### Scenario: Configuration-only run
- GIVEN a workspace source directory containing supported YAML/JSON configuration and an ADR
- AND no programming language is selected
- WHEN the existing analysis workflow runs
- THEN it invokes the structured-configuration adapter without invoking a language resolver
- AND it produces the normal run report, confidence assessment, JSON artifacts and CSV audit rows.

#### Scenario: Code source has no language selection
- GIVEN a selected source contains supported code files
- AND the language selection is absent or `none`
- WHEN the run is admitted
- THEN it fails with a typed input diagnostic before semantic analysis
- AND the run event/failure record does not claim collection completed.

### Requirement: Observation and coverage audit rows are additive and source-bound
The system MUST persist observations and collection reports as queryable CSV rows linked to exact source versions without modifying existing CSV table schemas.

#### Scenario: Observation is persisted
- GIVEN a collector emits an observation from a pinned artifact
- WHEN the run persists its audit data
- THEN the observation row records the run, observation identity, artifact ID/version/hash, locator, collector/version, resolution and redaction status
- AND the corresponding evidence and confidence rows remain joinable through run/evidence identifiers.

#### Scenario: Existing CSV snapshot is loaded
- GIVEN a legacy `poc-database` snapshot has all current tables but no observation or coverage tables
- WHEN a new workflow run loads it
- THEN the existing table headers remain unchanged
- AND new additive tables are initialized and accept rows.

#### Scenario: Collection is partial or fails
- GIVEN a source has unsupported files, parse failures, or missing source versions
- WHEN the collection stage completes
- THEN coverage rows and run events mark the limitation
- AND no absence-based supported conclusion is accepted.

#### Scenario: Parser error includes attacker-controlled text
- GIVEN malformed source content causes a parser exception containing a source excerpt
- WHEN the diagnostic is written to CSV, report, or Actions output
- THEN the stored diagnostic is bounded and sanitized
- AND the source excerpt is not copied into logs.

#### Scenario: Source excerpts contain credential-shaped literals
- GIVEN a code edge, ADR requirement, diff line, or syntax error includes a credential-shaped value or quoted literal
- WHEN evidence, model context, run artifacts, or CSV rows are produced
- THEN source string literals and known credential patterns are redacted from those outputs
- AND the original artifact hash and source locator remain available to establish which version was analyzed.

### Requirement: A versioned natural-language ADR corpus is auditable
The repository MUST maintain 50 unique synthetic ADR documents and an independent labeled manifest for offline evidence-collection evaluation.

#### Scenario: Corpus integrity is evaluated
- GIVEN the checked-in ADR corpus and its fixture manifest
- WHEN the offline corpus audit runs
- THEN it validates all 50 unique ADRs, domain labels, source hashes, exact evidence locators and expected dispositions
- AND reports extraction/evidence-mapping results separately from model semantic quality.

#### Scenario: Corpus case needs unsupported or runtime evidence
- GIVEN an ADR requirement needs an unavailable source capability or live runtime state
- WHEN the offline collector cannot establish the fact
- THEN the expected result remains inconclusive
- AND the corpus audit does not treat missing observations as compliance.
