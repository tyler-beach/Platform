## MODIFIED Requirements

### Requirement: Evaluate by requirement kind, not ADR identifier

The shared evaluation engine MUST decide deviation, alignment, inapplicability, and inconclusiveness using a typed requirement kind and provenance-bound observations. Evaluation MUST NOT branch on ADR identifiers. Supported kinds MUST include `numeric_max`, `numeric_min`, `resource_present`, `boolean_required`, `set_membership`, and `dependency_forbidden`.

#### Scenario: Numeric minimum deviation
- **GIVEN** an approved `numeric_min` requirement and a matching observation below the minimum
- **WHEN** the engine evaluates the requirement
- **THEN** the outcome is `supported_deviation`

#### Scenario: Forbidden dependency deviation
- **GIVEN** an approved `dependency_forbidden` requirement and a matching boolean observation `true` (relationship present)
- **WHEN** the engine evaluates the requirement
- **THEN** the outcome is `supported_deviation`
