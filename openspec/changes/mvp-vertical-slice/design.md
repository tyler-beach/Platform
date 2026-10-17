# Design: implementation readiness before the first code slice

## User journey

The bounded journey begins with one code-change snapshot and one known ADR artifact/version. The system resolves identity and scope, establishes ADR applicability, packages deterministic evidence, executes a bounded assessment when evidence/policy permit, validates the candidate against its exact evidence package, persists an inspectable outcome, and leaves consequential disposition to a human reviewer.

A result is a point-in-time assessment of pinned inputs and pinned pipeline/model configuration. Current source freshness is a separate property checked before any future external publication.

## Result semantics

- **Supported deviation:** applicable decision plus evidence supporting a contradiction.
- **No deviation found:** sufficient evidence was reviewed for the bounded constraint and no contradiction was established; not a universal proof of compliance.
- **Not applicable:** available evidence establishes that the candidate ADR does not govern this source/scope. Keep it distinct from deviation and execution failure.
- **Inconclusive:** applicability or evidence is insufficient or contradictory for a defensible conclusion.
- **Technical failure:** a typed operational/contract failure prevented analysis from completing. It is not a finding outcome.

Severity, reviewer disposition, model confidence/quality and execution state remain independent fields.

## Boundary choices

- One known accepted ADR is in scope for the first slice; broad discovery and ranking are deferred.
- A pinned change snapshot is the behavioral input contract. The exact ingress adapter (GitHub, supplied diff or another source) requires the decision packet to be reviewed before implementation.
- Step Functions remains the recommended owner of asynchronous lifecycle; database business state and durable dispatch must reconcile with that lifecycle.
- Model output is a candidate only. Application validation checks schema, evidence identity/version/location, applicability and domain rules.
- No model-controlled tools, code/ADR mutation or AI-only merge blocking.
- Synthetic fixtures are the first test corpus; proprietary source is excluded until data-processing approval exists.

## Review before implementation

The MVP decision packet is authoritative for current decision status. The proof matrix is the checklist for planned evidence. Where this design and a pre-existing contract conflict, create a focused contract decision/change before implementation rather than silently choosing one.

The proposal deliberately does not settle workflow mode, exact limits, dispatch mechanism, tenancy topology, data retention or API hosting. These require named owner approval or measurement.
