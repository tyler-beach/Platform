## ADDED Requirements

### Requirement: Behavioral changes have testable requirement traceability

A behavior change MUST link each changed requirement to observable scenarios and planned or actual verification evidence.

#### Scenario: A requirement changes before implementation

- GIVEN an OpenSpec change adds or modifies a behavioral requirement
- WHEN the change is reviewed for implementation
- THEN each requirement includes at least one observable Given/When/Then scenario
- AND tasks identify the unit, contract, integration, resilience, security or AI-evaluation proof that will verify it
- AND unresolved high-impact decisions are clearly marked for human approval.

#### Scenario: A regression is fixed

- GIVEN a defect has a reproducible observable failure
- WHEN practical
- THEN a regression test is added and shown failing for the expected reason before the minimal fix
- AND the test passes after the fix
- AND the relevant contract and regression suite run.

### Requirement: Deterministic domain policy is isolated from effects

Deterministic domain policy MUST operate over explicit values and versions wherever feasible; network, storage, time, randomness, model and publication effects MUST be explicit.

#### Scenario: Applicability is unit-tested

- GIVEN a fixed snapshot of decision status, scope, relationships and policy version
- WHEN applicability is evaluated repeatedly
- THEN the result is deterministic
- AND the test requires no live database, AWS or model provider
- AND infrastructure errors are not encoded as no-deviation outcomes.

### Requirement: OpenSpec archive follows verified behavior

A change MUST NOT be treated as complete or archived as shipped until acceptance scenarios and required tests/evaluations have been verified or a documented reviewed exception exists.

#### Scenario: A required evaluation was skipped

- GIVEN a prompt/retrieval/finding-policy change requires labeled evaluation
- AND the evaluation was not run
- WHEN a reviewer considers merge/archive
- THEN the missing evaluation is disclosed
- AND the change remains incomplete unless a specific exception is reviewed and recorded
- AND specs are not represented as proven production behavior.
