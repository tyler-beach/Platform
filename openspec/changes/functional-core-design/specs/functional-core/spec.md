# Functional core and explicit effects

## Purpose
Make domain analysis deterministic and composable while isolating infrastructure and model side effects.

## ADDED Requirements

### Requirement: Domain policy uses explicit inputs
Domain policy MUST be implemented as deterministic functions of explicit values and policy versions whenever feasible.

#### Scenario: Applicability is evaluated
- GIVEN the same ADR metadata, component relationships, scope facts and policy version
- WHEN applicability is evaluated multiple times
- THEN the deterministic result is the same
- AND no hidden database, clock, network or model call influences the decision.

### Requirement: Effects are explicit
The system MUST isolate network, database, filesystem, clock, randomness, workflow and model operations at explicit adapter or use-case boundaries.

#### Scenario: Domain logic is tested
- GIVEN a unit test for applicability or evidence validation
- WHEN the test executes
- THEN it can run without live AWS, database or Anthropic dependencies
- AND tests use explicit fixtures/inputs for external facts.

### Requirement: Stage outputs are safely owned
The system MUST define ownership for values passed between processing stages and MUST NOT mutate a stage output after it is handed off.

#### Scenario: Evidence package moves between stages
- GIVEN an evidence package is passed to a model assessment stage
- WHEN downstream code consumes it
- THEN upstream code does not mutate shared maps/slices/pointers that could change the request or invalidate audit evidence.

### Requirement: Evidence ordering is canonical
The system MUST use stable ordering when evidence order affects prompts, fingerprints, serialized outputs or regression results.

#### Scenario: Candidate evidence is assembled
- GIVEN the same set of evidence candidates and selection policy
- WHEN an evidence package is assembled
- THEN ordering and truncation are deterministic
- AND stable identifiers and source-version references are preserved.

### Requirement: Domain outcomes are separated from execution errors
The system MUST distinguish outcomes such as supported deviation, potential deviation, no deviation found and inconclusive from technical failures such as timeout, permission denial or provider outage.

#### Scenario: Provider call times out
- GIVEN an assessment cannot complete because a provider call times out
- WHEN the error is handled
- THEN it is recorded as an execution failure or retryable stage error
- AND is not represented as no deviation found.

### Requirement: External effects are retry-safe
The system MUST apply idempotency and deduplication at effectful boundaries that create jobs, persist findings or publish results.

#### Scenario: Worker execution is replayed
- GIVEN an event/worker attempt is repeated due to timeout or retry
- WHEN the stage executes again
- THEN it does not create duplicate logical jobs/findings/comments
- AND preserves audit history for the repeated attempt.
