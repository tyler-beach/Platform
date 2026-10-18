# Evaluation and human-feedback loop

Pathfinder has two offline evaluation tracks. Keep their claims separate.

## 1. Labeled detector regression suite

Run from the repository root:

```sh
python -m unittest discover -s .poc/tests -v
python .poc/evaluation/evaluate.py --provider mock --output-dir /tmp/pathfinder-eval
```

The 20 labeled cases currently exercise one narrow domain: whether a request path crosses an asynchronous boundary before calling a remote provider. They cover direct and indirect calls, queue/worker behavior, local validators, conditional paths, absent normative requirements, and unresolved dispatch.

The report includes:
- Three-way confusion matrix and exact accuracy.
- Binary precision/recall/F1 for clear gold labels; ambiguous cases are not counted as false positives or negatives.
- Decision coverage and ambiguous-case escalation.
- Review-gate threshold sweep.
- Breakdown by graph/scenario behavior, to expose local failure clusters.
- SHA-256 fingerprint of the exact JSONL corpus and recorded run configuration.

The mock provider is deterministic and useful for regression tests of the current rules. It is not an independent semantic judge. The Anthropic provider is opt-in and makes live, potentially billable model calls. Do not use aggregate numbers as production-quality estimates: the cases are synthetic and have not been independently adjudicated.

## 2. Natural-language ADR / evidence collection audit

```sh
python .poc/evaluation/evaluate_adr_corpus.py --output-dir /tmp/pathfinder-corpus
```

This audits 50 synthetic ADRs and their pinned fixtures. It verifies source hashes and whether the deterministic configuration collector emits expected facts. It does not invoke a model and does not measure whether the system correctly interprets the natural-language ADR.

The corpus has 35 declared-configuration facts and 15 cases requiring unavailable runtime-state evidence. Those runtime cases should remain inconclusive rather than treating missing telemetry as compliance.

## 3. Human feedback is a candidate pipeline, not automatic learning

1. Generate a deterministic probability sample and a separate risk-triage queue.
2. Create/reconcile GitHub issues for sampled review units. Issues are intake, not the authoritative review ledger.
3. Record a reviewer disposition as an append-only event with evidence references and a concise rationale.
4. Record adjudication separately. A disposition alone is not ground truth.
5. Export only explicitly approved, adjudicated events with a known training/validation split and required provenance.
6. Review the exported candidate, create or update a versioned fixture, and have a second reviewer confirm the gold label.
7. Run the complete regression suite and compare against the previous report before changing the baseline.
8. Never feed holdout cases into prompts, thresholds, training candidates, or routine iteration. Keep holdout data separate and access-controlled.

The promotion tool exports candidates only; it does not modify `.poc/evaluation/cases.jsonl`. A missing split is rejected rather than defaulting to training. Risk-triage selections have no population inclusion probability and must not be combined with weighted probability-sample estimates.

## 4. What is not a production gate yet

The suite does not currently provide an independently adjudicated holdout, representative production sample, statistically justified release thresholds, or calibrated probabilities. The repository’s tests and green CI only prove the checks actually run. Before production integration, appoint independent reviewers, establish a locked holdout, agree thresholds before evaluating it, and record the source/version provenance for every gold label.
