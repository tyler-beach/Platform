## Contract review

- [ ] 1.1 Review and approve the observation envelope, source locator/provenance requirements, and explicit collection coverage contract.
- [ ] 1.2 Decide the smallest initial set of reusable evidence capabilities and observation kinds; avoid defining a universal ontology.
- [ ] 1.3 Define how requirement interpretation records applicability, obligation, evidence needs, exceptions, ambiguity, and reviewer disposition without replacing ADR source text.
- [ ] 1.4 Select the first vertical slice and its supported source adapter(s); keep the assessment contract independent from adapter language.

## Implementation after review

- [ ] 2.1 Add domain types and validation for observations, collection reports, capability needs, source references, and resolution status.
- [x] 2.2 Add an adapter contract and migrate one existing language analyzer to emit the shared observation envelope without losing call-graph detail.
- [x] 2.3 Add a second, non-language source adapter or fixture to prove the contract covers configuration/resource evidence.
- [ ] 2.4 Add requirement evidence planning that selects adapters by capability and keeps ADR applicability separate from source language.
- [ ] 2.5 Add derived behavior-claim validation requiring observation links, versioned derivation, and supporting/contradicting evidence.
- [x] 2.6 Add coverage-aware outcome classification so unsupported/partial collection cannot yield a false absence-based conclusion.

## Verification and rollout

- [ ] 3.1 Add RED-first domain tests for provenance, observation compatibility, coverage gates, unknown capability, and unsupported negative evidence.
- [ ] 3.2 Add equivalent-behavior fixtures across at least two languages and assert compatible language-neutral observations.
- [ ] 3.3 Add cross-source fixtures for an ADR requirement backed by both source configuration and code; verify mixed or missing evidence becomes inconclusive.
- [ ] 3.4 Add adversarial tests for fabricated observation IDs, stale source versions, forged locators, prompt injection, and unsupported semantic summaries.
- [ ] 3.5 Extend the labeled evaluation set for generic ADR requirements; report evidence-link validity, outcome/abstention, and before/after results.
- [ ] 3.6 Run focused and applicable checks, record actual results, reconcile current-state specs, and archive only after reviewed acceptance scenarios pass.
