## ADDED Requirements

### Requirement: Evaluate by requirement kind, not ADR identifier

The shared evaluation engine MUST decide deviation, alignment, inapplicability, and inconclusiveness using a typed requirement kind and provenance-bound observations. Evaluation MUST NOT branch on ADR identifiers.

#### Scenario: Numeric maximum deviation
- **GIVEN** an approved `numeric_max` requirement and a matching observation whose value exceeds the limit
- **WHEN** the engine evaluates the requirement
- **THEN** the outcome is `supported_deviation`
- **AND** accepted evidence IDs and provenance are recorded

#### Scenario: Boolean required alignment
- **GIVEN** an approved `boolean_required` requirement and a matching observation with value `true`
- **WHEN** the engine evaluates the requirement
- **THEN** the outcome is `no_deviation_found`

#### Scenario: Set membership deviation
- **GIVEN** an approved `set_membership` requirement with an approved set and a matching observation whose value is outside that set
- **WHEN** the engine evaluates the requirement
- **THEN** the outcome is `supported_deviation`

#### Scenario: Unsupported kind remains unavailable
- **GIVEN** a requirement whose kind is not in the engine kind catalog
- **WHEN** evaluation is attempted
- **THEN** the call fails closed with a validation error rather than inventing a result

### Requirement: Bind collectors by predicate capability

Collectors MUST declare the predicates they can emit. Session TTL and PDB checks MUST obtain observations through collectors registered for those predicates rather than through ADR-specific evaluators.

#### Scenario: TTL uses shared numeric evaluation
- **GIVEN** a normalized session TTL case with pinned JSON evidence above the maximum
- **WHEN** investigation runs
- **THEN** the decision is produced by the shared engine `numeric_max` handler
- **AND** the persisted TTL result contract still fingerprints deterministically

#### Scenario: Unknown predicate cannot invent evidence
- **GIVEN** a predicate with no registered collector capability
- **WHEN** collection is requested through the registry
- **THEN** collection fails closed with an explicit capability gap

### Requirement: Normalize ADR prose into approved typed requirements

A normalizer MUST validate proposed typed requirements against the kind and predicate catalog, preserve ADR span provenance, and require an approval state before evaluation treats the requirement as authoritative. Ambiguous or unsupported proposals MUST remain `unnormalized` or rejected rather than becoming confident findings.

#### Scenario: Approve a valid typed candidate
- **GIVEN** a proposed requirement with supported kind, known predicate, subject, and ADR source span
- **WHEN** a human approval state is set to `approved`
- **THEN** the normalized record is eligible for shared evaluation

#### Scenario: Reject unsupported structure
- **GIVEN** a proposed requirement missing a required field or using an unknown predicate
- **WHEN** normalization validation runs
- **THEN** the candidate is not approved
- **AND** no observation or finding is synthesized
