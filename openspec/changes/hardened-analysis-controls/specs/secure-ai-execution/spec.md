## ADDED Requirements

### Requirement: Model invocations reserve cumulative job budget

The system MUST enforce concurrency-safe cumulative token, cost, call/retry and deadline budgets across all model invocations belonging to one job.

#### Scenario: Concurrent branches request model budget

- GIVEN two workers attempt model calls for the same job concurrently
- AND the combined reserved usage would exceed the configured job limit
- WHEN each worker requests admission
- THEN the durable reservation/ledger permits only the work that fits policy
- AND rejected work does not call the provider
- AND the decision and remaining budget are observable.

#### Scenario: Retry and verification follow initial assessment

- GIVEN the initial assessment used part of the job budget
- WHEN a retry, repair or optional verifier is considered
- THEN the operation uses the remaining shared budget and original job deadline
- AND it is stopped or skipped when the remaining allowance is insufficient
- AND it cannot reset the budget by replaying the API request.

### Requirement: Provider usage reconciles reservations

The system MUST retain estimated and provider-reported usage/cost separately and reconcile each attempt against the effective price configuration version.

#### Scenario: Provider response returns actual usage

- GIVEN a model call completes with provider-reported token usage
- WHEN the harness processes the response
- THEN the attempt records request ID, model/configuration versions, usage categories, estimated cost and reconciled cost
- AND unused reservation is released safely
- AND cumulative spend reflects the reconciled attempt.

#### Scenario: Request times out after possible provider acceptance

- GIVEN the client cannot determine whether a request reached the provider
- WHEN the call deadline is exceeded and usage is unknown
- THEN the attempt is marked usage-unknown/pending reconciliation
- AND a conservative budget reservation/charge remains until safely reconciled
- AND retry admission checks the same job budget.

### Requirement: Evidence compaction is deterministic and traceable

The system MUST compact oversized evidence packages using a versioned deterministic policy and MUST record omitted evidence identifiers and reasons.

#### Scenario: Required evidence cannot fit within limits

- GIVEN the selected evidence exceeds the input/context or spend policy
- AND required evidence cannot be retained within the configured budget
- WHEN the harness prepares a request
- THEN it does not silently drop required evidence to force an answer
- AND the job returns an explicit incomplete/inconclusive or review-required result without an unbounded model call.
