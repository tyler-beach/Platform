# Cross-domain ADR requirement evaluation

## Scope

This suite adds **160 synthetic scenario cases**: 20 each for session TTL, pod disruption budgets, sensitive data in logs, asynchronous provider processing, approved exceptions, runtime-evidence sufficiency, encryption at rest, and least-privilege authorization. Each type has 16 development cases and 4 locked holdout cases. The locked split is not used to select rules during a tuning pass.

## Run

```sh
python .poc/evaluation/requirements/evaluate_requirements.py
python -m unittest .poc/tests/test_requirement_corpus.py
```

The report is written to `.poc/evaluation/requirements/latest-report.json`, including a dataset SHA-256, per-type development/holdout metrics, confusion matrices, and per-case outcomes.

## Label provenance and limits

Labels are **provisional synthetic scenario-specification labels**. The facts are deliberately structured so the initial evaluator can be checked against explicit scenarios and evidence states. They are not independent human adjudications, real production observations, or estimates of production accuracy. Every case is marked `independent_adjudication_status: pending`; no independent-review result is invented. Use the included labels as regression oracles for the current deterministic rules, not as proof the rules generalize.

A blank review worksheet is provided at `.poc/evaluation/requirements/adjudication-template.csv` with one row per case. Before describing this as an independently adjudicated benchmark, have a reviewer who did not author the rules examine the requirement, evidence, rationale, applicability, and expected disposition; record reviewer identity/role, adjudicated label, evidence rationale, and disagreement resolution. Do not copy the provisional label into the adjudicated-label field without independent review. Keep locked cases inaccessible during rule tuning and refresh them after changes are accepted.

- Encryption at rest compares the effective active resource setting; missing or non-production observations remain ambiguous. This simplified fixture does not establish key strength or key-policy correctness.
- Least-privilege authorization relies on a pinned assessment of effective permissions; missing active-policy evidence remains ambiguous. The fixture does not parse IAM or Kubernetes policy semantics itself.

## Conservative disposition rules

- Session TTL compares the effective active value with the pinned maximum. Missing active config or uncertain exception status is ambiguous.
- PDB checks require workload applicability, effective PDB presence, selector match, and comparable minAvailable/required values. Missing deployment overlays remain ambiguous.
- Logging checks require evidence about observed sensitive values and verified redaction. Source code alone is not proof of production log behavior.
- Async processing requires a resolved dispatch and evidence about the request-path boundary; unknown waits or runtime paths remain ambiguous.
- Exceptions count only when approval, expiry, and scope are verified. An unused exception is not a deviation.
- Runtime evidence must be present, fresh, source-pinned, and applicable. Missing/stale/conflicting evidence is ambiguous.

This suite does not connect to Aurora, Bedrock, Kubernetes clusters, logging backends, or exception registries. Those adapters require separate integration tests with captured, provenance-preserving evidence.
