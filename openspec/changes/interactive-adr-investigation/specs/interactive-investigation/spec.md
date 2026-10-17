## ADDED Requirements

### Requirement: Explore a language-neutral architecture decision

The demo MUST allow a visitor to select an example ADR and inspect its required behavior, an illustrative observation, a candidate finding, evidence references, analysis stages, and coverage gaps without leaving the demo page.

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

### Requirement: Express session lifetime and disruption availability as behavioral constraints

The pod disruption budget ADR MUST require an effective budget aligned with an approved availability objective and workload topology. Resource existence alone MUST NOT establish compliance. Missing or conflicting scope evidence MUST lead to an inconclusive assessment.

The session TTL ADR MUST define a 60-minute absolute maximum from session establishment. Activity MUST NOT extend the same session beyond that maximum. Assessment MUST consider renewal and server-side acceptance behavior rather than relying only on one configured timeout or token claim.
