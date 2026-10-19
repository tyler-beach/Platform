## Contract and design review

- [x] 1.1 Review proposal, role model, evidence validation, token limits, and opt-in policy before implementation.
- [x] 1.2 Validate the OpenSpec change and reconcile wording with the active language-neutral-evidence proposal.

## RED-first domain behavior

- [x] 2.1 Add failing tests for role inference and role-preserving package observations.
- [x] 2.2 Add failing tests for exact unique quote anchoring, ambiguous quotes, invalid predicate/subject/value, forged provenance, and deterministic evidence IDs.
- [x] 2.3 Add failing tests proving the same fact from spec and code yields separate role-specific evaluations and missing role evidence is inconclusive.
- [x] 2.4 Add failing tests for semantic opt-in, token-budget denial, one-call maximum, no retry, deadline, secret-like input skip, and deterministic fallback.

## Implementation

- [x] 3.1 Implement the role-aware common evidence shape and validate legacy observations compatibly.
- [x] 3.2 Implement the bounded direct Anthropic client using token-count preflight and schema-constrained evidence-only output.
- [x] 3.3 Implement deterministic quote resolution and application-owned evidence/provenance construction; reject invalid candidates.
- [x] 3.4 Route both specification and implementation artifacts through semantic normalization when opted in; retain deterministic extraction when disabled/skipped.
- [x] 3.5 Evaluate and report by evidence role using the same generic engine; keep role-specific outcomes separate.
- [x] 3.6 Wire opt-in repository variable, Anthropic secret, and model ID through both GitHub workflows with minimum permissions.
- [x] 3.7 Update issue form guidance, first-run/operations docs, and extraction metadata to explain limits, setup, and cost bounds.

## Verification and PR

- [x] 4.1 Extend synthetic labeled fixtures with non-patterned technical prose, equivalent specification/code facts, ambiguity, unsupported claims, and missing evidence.
- [x] 4.2 Run Go unit/race tests, vet, pure-domain checks, OpenSpec validation, workflow YAML parsing, and relevant repo checks; report that no Go fuzz harness exists and live Anthropic evaluation was not run.
- [x] 4.3 Review secrets/logging, prompt injection, output-validation, retry/deadline, token-budget, and duplicate-run behavior adversarially.
- [x] 4.4 Reconcile the current-state OpenSpec spec and documentation; leave the change active if any acceptance proof is outstanding.
- [ ] 4.5 Push the isolated branch and open a reviewable PR; do not merge it.
