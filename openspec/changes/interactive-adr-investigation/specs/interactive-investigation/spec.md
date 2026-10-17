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

#### Scenario: Assess the session expiration boundary
- **GIVEN** a session has been established and the applicable policy sets a 60-minute maximum
- **WHEN** the session reaches the maximum lifetime
- **THEN** the system rejects the existing session for authenticated access
- **AND** activity alone cannot extend that same session beyond the boundary
- **AND** missing evidence about renewal or server-side acceptance is reported as inconclusive.

#### Scenario: Assess an effective disruption budget
- **GIVEN** an availability-sensitive workload has a declared availability objective and replica topology
- **WHEN** the effective disruption budget is evaluated
- **THEN** the assessment checks that the budget selects the intended workload and constrains voluntary disruption consistently with the objective
- **AND** a missing or mismatched workload relationship is not treated as compliance.
