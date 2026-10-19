# paste-observation-extraction Specification

## MODIFIED Requirements

### Requirement: Extract typed observations from pasted tech-spec or code

When an evidence package includes technical-specification and/or implementation content and no observations, the system MUST normalize the artifacts into typed observations for allowlisted catalog predicates. By default this MUST use deterministic extraction without a model call. When semantic extraction is explicitly enabled and configured, the evaluator MUST use the bounded semantic normalizer defined in `semantic-evidence-normalization`; its output MUST satisfy the same provenance and validation contract. Observations MUST preserve whether they represent design assertions or implementation facts and MUST pin artifact digests/locators. Missing or unsupported evidence MUST remain inconclusive.

#### Scenario: Markdown tech spec yields extractable observations
- **GIVEN** a package with markdown tech-spec content describing a catalog-supported requirement and no observations array
- **WHEN** extraction and package evaluation run
- **THEN** deterministic extraction may emit a matching observation when its configured patterns match
- **AND** when semantic extraction is opted in, non-patterned phrasing may emit a validated `design_assertion` observation
- **AND** unsupported or uncertain statements remain inconclusive

#### Scenario: Code paste is normalized through the shared envelope
- **GIVEN** Go, Python, YAML, JSON, or other supported implementation content
- **WHEN** extraction runs
- **THEN** validated observations use the common evidence envelope with role `implementation_fact`
- **AND** source-specific parsing or semantic interpretation does not create an ADR-specific downstream flow

#### Scenario: Existing deterministic extraction remains the no-model default
- **GIVEN** semantic extraction is disabled
- **WHEN** the issue package is evaluated
- **THEN** no Anthropic request is made
- **AND** the existing deterministic extractor remains available

#### Scenario: Secrets and unsupported source evidence do not become model input or compliance
- **GIVEN** an input matches a supported credential-like detector or evidence cannot be safely located
- **WHEN** semantic extraction runs
- **THEN** the detected source is not transmitted or the unlocatable candidate is rejected
- **AND** no missing observation is interpreted as alignment
