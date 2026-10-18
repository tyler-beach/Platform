# ADR Deviation Evaluation Iterations

This log records iterative runs of the **same 20-case synthetic corpus** in `.poc/evaluation/cases.jsonl`. The corpus fingerprint was unchanged across the three runs below. Each iteration changed deterministic assessment/evidence-linkage rules; results therefore show regression progress on this fixture set, **not** an independent estimate of production accuracy.

## Run history

| Iteration | GitHub Actions run | Three-way exact match | Clear-case precision | Clear-case recall | Ambiguous-case escalation | Main finding |
|---|---|---:|---:|---:|---:|---|
| Baseline | [39131006418](https://github.com/tyler-beach/Platform/actions/runs/39131006418) | 55% (11/20) | 75% | 100% | 37.5% (3/8) | Local validator names were mistaken for providers; queue/outbox flows were not recognized; several conditional/approximate paths were overcalled. |
| Iteration 2 | [39131969660](https://github.com/tyler-beach/Platform/actions/runs/39131969660) | 90% (18/20) | 100% | 66.7% | 100% (8/8) | Provider-target matching and explicit async-boundary recognition removed false positives and escalated ambiguous cases. Two helper-mediated violations were downgraded because the requirement-to-observation link did not establish the inline behavior. |
| Iteration 3 | [39132158753](https://github.com/tyler-beach/Platform/actions/runs/39132158753) | 100% (20/20) | 100% | 100% | 100% (8/8) | Evidence linkage now permits a contradiction link for a helper-mediated finding only when changed-line evidence explicitly describes synchronous/inline behavior or the absence of an async boundary. |

**Corpus SHA-256:** `1d8a2f9bdf8bbd0bc732047a1123ea6ecc27c761cd5b5706b88a8b9c89c7d850`

## What the current result means

- All 20 labeled synthetic cases matched their expected three-way disposition in iteration 3: 6 deviation, 6 no-deviation, 8 ambiguous.
- The 12 clear cases had 6 true positives, 0 false positives, 0 false negatives, and 6 true negatives.
- All 8 ambiguous cases were escalated rather than turned into a definitive no-deviation or supported-deviation result.
- The model now treats a local method named `Assess` as insufficient evidence of a remote provider call, recognizes queue/outbox boundaries, and distinguishes a resolved direct call from conditional, approximate, or unresolved dispatch.
- Helper-mediated contradictions need explicit evidence that the call executes inline/synchronously; a call edge to a helper alone is not enough.

## Guardrails and next validation

These are hand-authored synthetic fixtures whose expected labels are provisional. The perfect score is expected to be vulnerable to overfitting because the rules were iterated against this same set. Do **not** describe it as production accuracy, calibrated confidence, or proof that a real ADR is compliant.

Next validation should use a frozen, independently adjudicated corpus not used during rule development, including real code paths, language-specific call graph limitations, configuration-based requirements (e.g. session TTL and Kubernetes PDBs), missing/stale evidence, runtime deployment selection, and contradictory ADR/spec versions. Keep ambiguous cases in the evaluation and preserve human review for supported findings.
