## ADDED Requirements

### Requirement: Filter catalog requirements by applicability before evaluation

Before kind evaluation, Pathfinder MUST determine which typed requirements are in scope for the pinned package using ADR lifecycle status and explicit applicability metadata. Requirements that are not in scope MUST receive `not_applicable` outcomes and MUST NOT be treated as evidence of compliance. When no requirements are in scope, the report MUST surface that disposition distinctly from “all aligned.”

#### Scenario: Out-of-scope domain is not_applicable
- **GIVEN** a package scoped to domain `identity` and a catalog requirement tagged only for domain `cloud`
- **WHEN** evaluation runs with applicability filtering
- **THEN** that requirement’s outcome is `not_applicable`
- **AND** it does not count as aligned compliance

#### Scenario: No applicable requirements is not all_aligned
- **GIVEN** a package whose scope matches no active catalog requirements
- **WHEN** evaluation completes
- **THEN** aggregate status is not `all_aligned`
- **AND** the report identifies that no applicable requirements were evaluated

### Requirement: Catalog identity is recorded on the report

Each evaluation report MUST include catalog identity metadata (catalog id/name, manifest hash or version, and mode such as `synthetic` or `real`) so consumers can tell which ADR pack produced the outcomes.

#### Scenario: Report names the catalog pack
- **GIVEN** a successful package evaluation
- **WHEN** the report is written
- **THEN** it includes catalog identity fields sufficient to reproduce the pack version used
