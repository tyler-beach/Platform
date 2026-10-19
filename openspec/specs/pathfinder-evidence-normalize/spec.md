# pathfinder-evidence-normalize Specification

## Purpose
Define the deterministic Pathfinder evidence-normalize stage that turns package observations into a canonically ordered, provenance-bound list with explicit locator precision before catalog evaluation—without inventing observations or calling a model.
## Requirements
### Requirement: Normalize observations into a canonical provenance-bound shape

Before catalog evaluation, Pathfinder MUST normalize package observations into a deterministic list that binds each observation to artifact digest provenance, a typed locator, and an explicit `locator_precision`. Normalization MUST NOT invent observations or call a model.

#### Scenario: Valid observations gain precision and stable order
- **GIVEN** a `pathfinder-evidence-package-v1` with two valid observations supplied in reverse evidence_id order
- **WHEN** normalize runs
- **THEN** each observation includes `locator_precision` of `EXACT`, `APPROXIMATE`, or `UNAVAILABLE`
- **AND** each observation includes `normalizer_version`
- **AND** the output order is the canonical sort key, independent of input order

#### Scenario: Incomplete observation fails closed
- **GIVEN** an observation missing a required provenance field or typed locator
- **WHEN** normalize runs
- **THEN** normalization fails with a validation error
- **AND** no partial normalized list is returned for evaluation

#### Scenario: Span locator is exact
- **GIVEN** an observation locator of kind `paste_span` with line or byte span fields and an excerpt digest
- **WHEN** normalize runs
- **THEN** `locator_precision` is `EXACT`

#### Scenario: Symbolic locator is approximate
- **GIVEN** an observation locator of kind `yaml_resource` or `issue_claim` with a non-empty `value` and no span
- **WHEN** normalize runs
- **THEN** `locator_precision` is `APPROXIMATE`

### Requirement: Classify conflicting observations without silent resolution

Normalize MUST classify groups of observations that share the same predicate and subject but disagree on value. Classification MUST NOT drop or rewrite authored observation values; evaluation remains responsible for `conflicting_evidence` outcomes.

#### Scenario: Conflicting values are reported
- **GIVEN** two observations for the same predicate and subject with unequal values
- **WHEN** conflict classification runs
- **THEN** the pair is reported as a conflict group
- **AND** both observations remain in the normalized list

#### Scenario: Agreeing values are not conflicts
- **GIVEN** two observations for the same predicate and subject with equal values
- **WHEN** conflict classification runs
- **THEN** no conflict group is reported for that predicate and subject

### Requirement: Collect adapter preserves registry gates

The package collect adapter MUST continue to verify artifact content digests and predicate registry collectability, then MUST invoke normalize for the observation list. Collect MUST still refuse to synthesize missing observations.

#### Scenario: Unknown predicate remains rejected
- **GIVEN** an observation whose predicate is absent from the catalog registry
- **WHEN** collect runs
- **THEN** collect fails closed before evaluation
- **AND** normalize is not asked to accept the unknown predicate as valid catalog evidence

