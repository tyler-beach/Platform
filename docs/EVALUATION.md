# Evaluation and quality strategy

## Why this is part of the system
The detector can miss a real deviation, invent one, apply an irrelevant ADR, or generate a plausible claim without evidence. Unit tests cannot measure all of this. Maintain a versioned, labeled evaluation corpus and run it when prompts, models, retrieval, parsers or finding policy change.

## Corpus cases
Include: clear deviation; similar-looking non-deviation; applicable accepted ADR; proposed/rejected/superseded/out-of-scope ADR; conflicting spec/implementation; multiple applicable decisions; exception/waiver; ambiguous prose; insufficient evidence; renamed/moved symbol; config/infrastructure input; prompt injection; malformed output; stale version; duplicate event.

For each case store expected outcome, applicable decision IDs, acceptable evidence spans, review disposition, and rationale. Review and approve any proprietary source used in test data.

## Metrics
- **Detection:** precision, recall, false-positive/negative rate by category/severity, applicability accuracy.
- **Evidence:** citation-resolution rate, reviewer-rated evidence-support rate, source-location correctness, unsupported-claim rate, correct inconclusive behavior.
- **Retrieval:** recall@k/precision@k for applicable decisions and required specs.
- **Operations:** p50/p95 latency by stage, calls/tokens/cost per job, retry/failure rate, duplicate rate, review rate.
- **Usability:** reviewer agreement, time-to-triage, accepted/dismissed/deferred proportions.
- **Robustness:** performance by language/format, prompt injection success, model/provider drift.

## Methods
Use deterministic unit and golden tests for parsers, applicability rules, state transitions and citation validation; retrieval benchmarks; offline end-to-end labeled evaluations; adversarial security tests; human-reviewed samples; and canary/shadow comparisons. Model-as-judge can supplement, but cannot be the only judge of its own system.

## Release gates
Schema and evidence reference validation are hard gates. Critical security/tenant tests must not regress. Set numeric precision/recall targets only after measuring the representative pilot corpus. Every prompt/model change reruns the regression set. Keep merge blocking disabled until agreed quality and override policy are reviewed.

## Observability
Trace ingress, normalization, retrieval, deterministic analysis, each Anthropic call, validation, persistence and publication. Correlate by job ID/trace ID. Record model/prompt/schema version, evidence IDs, token usage, latency, retries and validation result. Avoid logging raw private source by default.

## Current PoC labeled evaluation

The executable baseline lives in `.poc/evaluation/cases.jsonl` and runs with:

    python .poc/evaluation/evaluate.py --provider mock --output-dir /tmp/adr-evaluation

The suite has 14 synthetic scenarios split across three expected dispositions: clear deviations, clear non-deviations, and ambiguous cases that should remain open to review. It deliberately tests boundaries that naive call-name heuristics can get wrong: helper methods that block on providers, a queue followed by a worker call, local validators named `Assess`, explicitly permitted synchronous calls, unresolved dynamic dispatch, conditional fallbacks, and approximate CHA edges.

The runner executes the current assessment adapter, applies the versioned evidence score and outcome guardrails, and writes both `evaluation.md` and `evaluation.json`. It reports three-way accuracy and confusion matrix, binary precision/recall/F1 on clear cases, escalation on ambiguous cases, and a score-threshold sweep that gates which model-proposed findings are sent forward as actionable. The sweep does not use score alone to predict whether a violation exists.

The default `mock` provider is offline and deterministic. It is useful for regression testing the harness and can expose limitations in the rules, but it is not evidence of live model quality. To evaluate live model behavior, run `--provider anthropic` only when the API key, expected cost, and test-data handling are explicitly approved.

**Dataset status:** the cases are initial, hand-authored expected dispositions, not independently adjudicated ground truth. Architecture reviewers should review the expected labels and evidence spans, add realistic repositories and real-world false-positive/false-negative examples, and version those changes before tuning operational thresholds. The evidence-strength score remains an explainable support rating—not a calibrated probability—and no unattended merge blocking is enabled.
