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
