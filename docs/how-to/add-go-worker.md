# How to add a Go worker

Workers are reusable, bounded operations. Step Functions owns distributed orchestration; each Lambda runs one stable unit of work and returns a typed result.

## Pattern

1. Define input DTO with immutable references, workspace/job IDs, stage/attempt identity, deadline/budget, and pipeline version.
2. Define output DTO with explicit outcome, produced-object references, validation metadata, and typed error category.
3. Keep deterministic transformation/policy in pure functions under a domain package.
4. Keep clock, randomness, DB, AWS, source API, Anthropic and telemetry interactions in explicit adapters/use cases.
5. Validate workflow/event inputs even if an upstream component validated them.
6. Make external effects idempotent with operation identity and persistence constraints.
7. Emit structured logs and spans from the [logging contract](../contracts/LOGGING_AND_AUDIT.md).
8. Add unit, adapter contract, replay/failure, and bounded integration tests.

## Worker rules

- Use idiomatic Go values/errors; no custom monadic Result/effects framework.
- Do not mutate maps/slices after handing them to another stage.
- Canonicalize collections before hashing, prompting or evaluation.
- Domain outcomes are distinct from technical errors such as timeout or provider outage.
- Model cannot select IAM actions, shell commands, workflow ARNs or arbitrary source URLs.
- Bound concurrency, retries, execution time, evidence size, tokens and cost.

## Testing checklist

- Deterministic outputs for equal inputs.
- No hidden I/O in core functions.
- Deadline/cancellation propagation.
- Duplicate event is idempotent.
- Retry exhaustion is typed and auditable.
- Invalid evidence refs rejected.
- Secret/source-content logging tests.
- Race tests for shared mutable state.
