# Orchestration and reliability

## Purpose
Process analysis jobs through bounded, observable, retryable stages without duplicate or inconsistent side effects.

## Requirements

### Requirement: Job lifecycle is explicit
Every job MUST have explicit states and terminal outcomes.

#### Scenario: Job succeeds
- GIVEN valid inputs and all required stages complete
- WHEN the result is committed
- THEN the job reaches a successful terminal status
- AND records pipeline and source versions.

#### Scenario: Non-retryable failure
- GIVEN invalid input, authorization error or unsupported format
- WHEN the failure is classified
- THEN the job fails with a typed diagnostic and correlation ID
- AND does not retry indefinitely.

### Requirement: Processing is idempotent
The system MUST handle duplicate source events without inconsistent duplicate side effects.

#### Scenario: Event is delivered twice
- GIVEN identical event identity and immutable versions
- WHEN the event is received more than once
- THEN the system reuses or safely reconciles job state
- AND avoids duplicate findings or publication.

### Requirement: External operations are bounded
Every external call MUST have a timeout and finite retry policy appropriate to its error class.

#### Scenario: Transient provider failure
- GIVEN a retryable network, rate-limit or provider error
- WHEN another attempt is allowed
- THEN the system applies bounded backoff and honours the overall deadline
- AND records the attempt/outcome.

#### Scenario: Retry budget exhausted
- GIVEN retry count or overall deadline is reached
- WHEN processing cannot continue
- THEN the job reaches a typed failure/review state
- AND preserves diagnostics for safe operator action.

### Requirement: Parallel branches have an aggregation policy
The system MUST define how independent analysis branches aggregate evidence and handle failures.

#### Scenario: Evidence branch fails
- GIVEN retrieval and static analysis run concurrently
- WHEN a branch fails or times out
- THEN the workflow follows explicit fail/retry/continue policy
- AND does not claim completeness when required evidence is missing.
