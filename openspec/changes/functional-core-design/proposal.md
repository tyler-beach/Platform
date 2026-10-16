# Change: make the platform functional-core / imperative-shell by design

## Why
The architecture values evidence provenance, explicit stages, validation and idempotency, but does not yet prescribe how to prevent hidden effects, shared mutable state, nondeterministic evidence ordering, or business policy scattered across workers and prompts.

## Proposed change
Adopt functional-core / imperative-shell as the preferred implementation pattern in Go. Define pure domain transformations and explicit effect boundaries; model valid outcomes and technical failures separately; make stage values versioned; canonicalize evidence ordering; and make external effects safe to retry.

## Scope
- Add an adversarial design review and Go examples.
- Update coding-agent guidance, Go tooling, AI pipeline, architecture and operational docs.
- Add OpenSpec requirements for pure domain decisions, explicit effects/failures, stable evidence and retry-safe side effects.

## Non-goals
- Adding a functional programming framework or custom monad/effect type system.
- Rewriting every external adapter as pure code.
- Deep-copying large source payloads at every stage.
- Claiming code compliance before implementation and tests exist.

## Acceptance criteria
- Domain policy can be unit-tested without database/network/model calls.
- Clock, ID generation, model output and external state are explicit dependencies.
- Evidence/finding serialization has stable ordering where ordering affects behavior.
- Domain outcomes are distinct from infrastructure/execution errors.
- Worker retries and publication are protected by idempotency semantics.
- Agent instructions require relevant tests and truthful reporting.
