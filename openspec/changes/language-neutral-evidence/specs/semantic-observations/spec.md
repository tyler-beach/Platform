# Semantic observations

## ADDED Requirements

### Requirement: Source adapters emit versioned, language-neutral observations
The system MUST represent collected implementation facts through a source-neutral observation contract while preserving adapter-specific provenance and resolution details.

#### Scenario: Equivalent behavior appears in different languages
- GIVEN two versioned implementations in different supported languages express the same relevant behavior
- WHEN their source adapters collect evidence
- THEN each emits compatible language-neutral observations for that behavior
- AND each observation retains its own artifact version, exact locator, collector version, and resolution basis.

#### Scenario: A source-specific fact cannot be normalized reliably
- GIVEN an adapter encounters syntax, dispatch, or configuration it cannot resolve
- WHEN it emits collection results
- THEN the limitation and unresolved evidence remain explicit
- AND it does not claim a stronger normalized fact than the source analysis supports.

### Requirement: ADR requirements are independent of implementation language
The system MUST assess applicable ADR requirements against relevant evidence capabilities rather than require the decision and implementation to share a programming-language label.

#### Scenario: Same ADR requirement applies to multiple languages
- GIVEN an applicable ADR has no language-specific limitation
- AND equivalent source-backed observations are collected from implementations in different languages
- WHEN the requirement is assessed
- THEN both implementations use the same requirement and assessment contract
- AND language metadata does not exclude otherwise applicable evidence.

#### Scenario: ADR explicitly limits applicability by language
- GIVEN an ADR explicitly scopes a requirement to a named language or runtime
- WHEN applicability is resolved
- THEN that language constraint is applied as decision scope
- AND it is not inferred merely from the selected source adapter.

### Requirement: Adapters are reusable by evidence source, not tailored to each ADR
The system MUST select reusable source adapters by required evidence capability and MUST NOT require a new parser or adapter solely because a new ADR introduces a requirement over already supported evidence.

#### Scenario: New requirement uses an existing evidence capability
- GIVEN a new ADR requirement concerns a fact that an available adapter already emits
- WHEN evidence planning runs
- THEN the existing adapter supplies the observation
- AND the requirement is evaluated without an ADR-specific parser.

#### Scenario: Requirement needs an unsupported evidence capability
- GIVEN no available adapter can collect evidence required by an ADR requirement
- WHEN assessment runs
- THEN the missing capability is reported
- AND the result remains inconclusive rather than treating missing evidence as compliance or deviation.

### Requirement: Derived behavior claims remain linked to observations
The system MUST treat summaries and semantic interpretations as derived claims and MUST require validated links to source-backed observations before they support an actionable finding.

#### Scenario: Summary describes behavior
- GIVEN a summary says a request path synchronously invokes an external service
- WHEN the summary is used in ADR assessment
- THEN it identifies the observation IDs, source references, derivation version, and resolution basis supporting the claim
- AND the summary text alone cannot validate a deviation.

#### Scenario: Derived claim conflicts with its source observations
- GIVEN a derived claim is inconsistent with or unsupported by its referenced observations
- WHEN validation runs
- THEN the claim is rejected or marked inconclusive
- AND it cannot support an actionable finding.

### Requirement: Evidence coverage constrains conclusions
The system MUST preserve collection coverage and MUST NOT infer absence or compliance from missing observations when relevant source collection is incomplete or unsupported.

#### Scenario: Partial source scan has no matching observation
- GIVEN a required adapter reports unsupported files, unresolved configuration, inaccessible source, or failed collection
- AND no matching observation was found
- WHEN a requirement is assessed
- THEN the outcome is inconclusive with the missing coverage identified
- AND absence is not treated as proof of compliance or deviation.

#### Scenario: Complete source scan has no matching observation
- GIVEN a requirement explicitly expects a discoverable source fact
- AND the relevant source scope is enumerated with sufficient validated coverage
- AND no matching observation exists
- WHEN the requirement is assessed
- THEN any absence-based conclusion follows the requirement's explicit policy
- AND cites the coverage report and source scope used.
