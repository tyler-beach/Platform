## MODIFIED Requirements

### Requirement: Explore a language-neutral architecture decision

The demo MUST allow a visitor to select an example ADR and inspect its required behavior, an illustrative observation, a candidate finding, evidence references, analysis stages, and coverage gaps without leaving the demo page. The staged flow MUST include an explicit Normalization stage that shows how ADR prose becomes a typed, approved requirement before shared evaluation.

#### Scenario: Switch between example decisions
- **WHEN** a visitor selects the pod disruption budget or session TTL example
- **THEN** the decision, observation, evidence, stage trace, and coverage gaps update together
- **AND** the example is labelled synthetic.

#### Scenario: Inspect evidence and stages
- **WHEN** a visitor selects an evidence reference
- **THEN** the selected source reference is displayed
- **WHEN** a visitor selects an analysis stage
- **THEN** the stage description updates and the selected stage is programmatically exposed.

#### Scenario: Record a local review choice
- **WHEN** a visitor chooses confirm, dismiss, or inconclusive
- **THEN** the selected review choice is visible
- **AND** the interface states that the choice is local to the demo and has not changed a production record.

#### Scenario: See normalization in the workflow map
- **WHEN** a visitor opens the signal-flow explorer
- **THEN** the stage strip includes Normalization between Scope and Evidence
- **AND** selecting the normalization node explains typed kind, predicate binding, and human approval before deterministic evaluation.
