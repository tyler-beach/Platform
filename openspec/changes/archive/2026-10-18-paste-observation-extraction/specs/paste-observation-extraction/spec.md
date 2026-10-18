## ADDED Requirements

### Requirement: Extract typed observations from pasted tech-spec or code

When an evidence package includes tech_spec and/or code content and does not supply observations, the system MUST run a deterministic paste extractor that emits zero or more typed observations for allowlisted catalog predicates. Extraction MUST NOT call a model to invent values. Observations MUST use catalog subjects and pin artifact digests/locators.

#### Scenario: Markdown tech spec yields extractable observations
- **GIVEN** a package with only markdown tech-spec content describing session TTL and encryption at rest, and no observations array
- **WHEN** extraction and package evaluation run
- **THEN** observations for the matched allowlisted predicates are present
- **AND** catalog evaluation produces at least one non-inconclusive outcome for those predicates

#### Scenario: Code paste detects secret-in-source without inventing absence
- **GIVEN** Python or Go source containing a hardcoded API key-like secret literal
- **WHEN** extraction runs
- **THEN** `security.secret_in_source.present` is emitted as `true` with a span locator
- **AND** source that contains no secret match does not emit `security.secret_in_source.present=false`

#### Scenario: Conflicting values fail closed
- **GIVEN** pasted content that asserts two different numeric values for the same predicate and subject
- **WHEN** extraction runs
- **THEN** no observation is emitted for that predicate+subject

#### Scenario: Issue intake accepts paste without observations JSON
- **GIVEN** a Pathfinder analyze issue with attestation, tech spec and/or code, and no observations JSON
- **WHEN** intake builds the package
- **THEN** extraction runs
- **AND** evaluation proceeds (empty extraction yields inconclusive coverage, not an intake hard-fail for missing observations)
