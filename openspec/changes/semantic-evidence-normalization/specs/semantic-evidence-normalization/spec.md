# semantic-evidence-normalization Specification

## Purpose

Normalize proposed design specifications and implementation artifacts into one source-versioned evidence contract, then evaluate all accepted evidence against each requirement in one shared pass while preserving source provenance.

## ADDED Requirements

### Requirement: Normalize heterogeneous artifacts into common evidence with source provenance

The Pathfinder package evaluator MUST represent facts extracted from technical specifications as `design_assertion` evidence and facts extracted from code, configuration, or runtime artifacts as `implementation_fact` evidence. Both roles MUST use the same typed observation envelope and downstream requirement evaluator. A model MUST NOT select or change an evidence role.

#### Scenario: Same requirement is evaluated once across spec and code
- **GIVEN** a package contains a technical specification and code that refer to the same predicate and subject
- **WHEN** both artifacts are normalized and evaluated
- **THEN** resulting evidence shares the same observation schema
- **AND** the spec evidence is labeled `design_assertion`
- **AND** the code evidence is labeled `implementation_fact`
- **AND** the requirement produces one result using all matching observations
- **AND** each cited observation retains its artifact-derived role in result provenance

#### Scenario: Conflicting source values remain visible in one result
- **GIVEN** a package contains a specification and code that assert different values for the same predicate and subject
- **WHEN** both artifacts are normalized and evaluated
- **THEN** one requirement result reports conflicting evidence as inconclusive
- **AND** provenance identifies the specification and code evidence that conflict

#### Scenario: Role is derived from the pinned source artifact
- **GIVEN** a package contains a manually supplied observation without `evidence_role`
- **AND** the observation identifies a pinned source artifact in the package
- **WHEN** the package is validated
- **THEN** the observation receives the role assigned by the trusted package adapter for that artifact
- **AND** its source provenance and value are otherwise validated as before

#### Scenario: Legacy observation without a package artifact remains implementation evidence
- **GIVEN** a legacy observation has a valid source hash but no matching package artifact and no role
- **WHEN** the package is validated
- **THEN** it receives `implementation_fact` for backward compatibility

#### Scenario: Model cannot promote design intent to implementation fact
- **GIVEN** the model response attempts to set or alter evidence role, source version, path, offsets, or evidence ID
- **WHEN** normalized evidence is constructed
- **THEN** those fields are derived from trusted package metadata and source content
- **AND** model-supplied values for those fields are rejected or ignored

### Requirement: Semantic normalization is bounded and opt-in

When semantic extraction is explicitly enabled and configured, the evaluator MUST make at most one generation request per workflow invocation. It MUST count the exact request shape before generation, reject requests beyond the 20,000 input-token ceiling, cap output at 4,000 tokens and 64 candidate facts, apply a 60-second request deadline, and perform no automatic generation retry or repair. When disabled, it MUST make no Anthropic network request.

#### Scenario: Disabled semantic path makes no provider request
- **GIVEN** semantic extraction is disabled
- **WHEN** a package with specification and code is evaluated
- **THEN** no token-count or generation request is made
- **AND** the deterministic extractor remains the selected path

#### Scenario: Oversized request stops before generation
- **GIVEN** token preflight reports more than 20,000 input tokens or cannot complete
- **WHEN** semantic extraction is enabled
- **THEN** no generation request is made
- **AND** the report records budget denial or preflight failure
- **AND** available deterministic evidence may still be evaluated without claiming semantic coverage

#### Scenario: One bounded semantic call
- **GIVEN** semantic extraction is enabled, configured, and within the input-token budget
- **WHEN** normalization runs
- **THEN** no more than one Messages generation request is issued
- **AND** its maximum output is 4,000 tokens and its deadline is 60 seconds
- **AND** actual input/output usage and configured model identity are recorded when returned

#### Scenario: Credential-like source is not sent
- **GIVEN** an input artifact matches a supported credential-like secret detector
- **WHEN** semantic extraction is enabled
- **THEN** the adapter does not transmit that source package to Anthropic
- **AND** the report records a safe skip reason without printing matched content

### Requirement: Validate semantic evidence against the pinned source

Semantic output MUST be treated as an untrusted candidate. The application MUST restrict candidate predicates, subjects, and value types to the loaded catalog registry; require an exact source quote; resolve that quote to exactly one location in the referenced artifact; and derive evidence identity, source digest, revision, path, role, and locator itself. Invalid candidates MUST NOT support alignment or deviation findings.

#### Scenario: Valid source quote produces evidence
- **GIVEN** a candidate uses an allowed predicate/subject/value and quotes text found exactly once in a pinned artifact
- **WHEN** normalization validates the candidate
- **THEN** the application constructs a typed evidence object with the exact source hash, revision, role, path, and computed locator

#### Scenario: Fabricated or ambiguous quote is rejected
- **GIVEN** a candidate quote is absent from the artifact or appears more than once
- **WHEN** normalization validates the candidate
- **THEN** it is rejected as evidence
- **AND** a catalog outcome cannot be supported by that candidate

#### Scenario: Unknown predicate or invalid value stays unresolved
- **GIVEN** semantic output contains an unknown predicate, unapproved subject, or incompatible value type
- **WHEN** output validation runs
- **THEN** the candidate is rejected
- **AND** relevant requirement results remain inconclusive unless other valid evidence supports them

#### Scenario: Prompt injection remains untrusted input
- **GIVEN** an artifact contains instructions to ignore the schema, alter roles, expose credentials, or change policy
- **WHEN** semantic normalization runs
- **THEN** the content is treated only as source data
- **AND** no policy, secret, permission, or tool behavior changes

### Requirement: Preserve extraction method, source provenance, and uncertainty

Reports MUST identify whether deterministic or semantic extraction ran and preserve model/prompt/schema versions and bounded usage metadata when semantic analysis ran. Each requirement MUST produce one evaluation over all accepted matching observations; source roles remain available in evidence provenance. Missing or unsupported evidence MUST remain inconclusive; model silence MUST NOT be interpreted as compliance.

#### Scenario: Spec-only input produces ordinary requirement results with source provenance
- **GIVEN** a package contains only a technical specification
- **WHEN** evaluation finishes
- **THEN** requirement results use the same schema and evaluation path as code input
- **AND** cited evidence provenance identifies the source as `design_assertion`

#### Scenario: Missing semantic fact is not aligned
- **GIVEN** an applicable requirement has no validated observation in any input artifact
- **WHEN** evaluation finishes
- **THEN** the single requirement outcome is `inconclusive`
- **AND** the report states that evidence was not established

#### Scenario: Provider failure does not masquerade as semantic success
- **GIVEN** token counting or generation fails
- **WHEN** deterministic fallback evidence is available
- **THEN** the fallback can be evaluated
- **AND** the report identifies semantic extraction as unavailable and does not claim it ran

