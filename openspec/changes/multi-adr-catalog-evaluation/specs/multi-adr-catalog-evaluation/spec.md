## ADDED Requirements

### Requirement: Evaluate a pinned package against a typed ADR catalog

The system MUST evaluate a pinned evidence package against an approved typed-requirement catalog and return one outcome per applicable requirement using the shared engine. Evaluation MUST NOT branch on ADR identifiers inside kind handlers.

#### Scenario: Multi-requirement mixed results
- **GIVEN** a pinned package with observations for several registered predicates
- **AND** an approved catalog containing requirements that use those predicates
- **WHEN** package evaluation runs
- **THEN** each applicable requirement receives `supported_deviation`, `no_deviation_found`, `not_applicable`, or `inconclusive`
- **AND** the aggregate summary reports counts and a `mixed` status when both deviations and alignments are present

#### Scenario: Missing observation stays inconclusive
- **GIVEN** an applicable catalog requirement whose predicate has no matching observation in the package
- **WHEN** package evaluation runs
- **THEN** that requirement outcome is `inconclusive`
- **AND** no fabricated observation is invented

### Requirement: Catalog ADRs are synthetic and typed

The expanded ADR set MUST be labeled synthetic/unadjudicated. Each catalog entry used for evaluation MUST have an approved typed requirement referencing a registered predicate and supported kind.

#### Scenario: Reject unknown predicate in catalog load
- **GIVEN** a catalog requirement whose predicate is not registered
- **WHEN** the catalog is loaded for evaluation
- **THEN** loading fails closed with a validation error
