## ADDED Requirements

### Requirement: Accepted jobs have durable dispatch intent

The system MUST persist a recoverable workflow-dispatch intent with the accepted job and idempotency record before acknowledging job acceptance.

#### Scenario: Workflow start is unavailable after job commit

- GIVEN the job, canonical request fingerprint and dispatch intent commit successfully
- AND Step Functions is temporarily unavailable
- WHEN the API returns acceptance and the dispatcher attempts to start the workflow
- THEN the pending intent remains durably discoverable
- AND reconciliation retries start within policy
- AND retries converge on the same logical job without duplicate findings
- AND dispatch lag is observable.

#### Scenario: Dispatcher crashes after workflow start

- GIVEN the dispatcher successfully starts a workflow
- AND crashes before recording the start result
- WHEN a new dispatcher claims the expired intent
- THEN duplicate start attempts are reconciled by stable identity/adapter semantics
- AND stale claim ownership cannot overwrite newer dispatch state
- AND the job retains one authoritative lifecycle.

### Requirement: Effectful stages are replay-safe

Each externally observable logical effect MUST have an idempotency identity and MUST tolerate at-least-once delivery.

#### Scenario: Worker times out after persistence

- GIVEN a worker commits a finding but times out before acknowledging the stage
- WHEN Step Functions retries the worker
- THEN the same logical finding is not duplicated
- AND the repeated attempt is recorded as attempt telemetry/audit where appropriate
- AND immutable source and prior run provenance remain unchanged.

#### Scenario: Cancellation races with publication

- GIVEN cancellation and publication are concurrent
- WHEN one operation wins the current-state/fencing check
- THEN only policy-permitted effects commit
- AND a completed external effect is not described as rolled back
- AND the race outcome is auditable.
