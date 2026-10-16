## Design and implementation guidance
- [ ] Review and approve functional-core / imperative-shell conventions.
- [ ] Identify hidden effects in domain decision logic and move them to explicit boundaries.
- [ ] Define stage-specific input/output values for the first analysis vertical slice.
- [ ] Add typed domain outcomes and classified execution errors.
- [ ] Canonicalize evidence ordering and finding fingerprints.
- [ ] Document ownership of Go structs, maps, slices and pointers across stages.

## Tests and reliability
- [ ] Unit-test core rules without DB/network/Anthropic dependencies.
- [ ] Test that same explicit inputs and policy version yield same deterministic output.
- [ ] Test unknown/wrong-version evidence refs and invalid state transitions.
- [ ] Add idempotency/duplicate-delivery tests for job creation, persistence and publication.
- [ ] Add race/concurrency tests for any shared worker state.
- [ ] Ensure model calls are explicit effects and model behavior is evaluated separately from deterministic core.
- [ ] Report actual checks run and remaining gaps.
