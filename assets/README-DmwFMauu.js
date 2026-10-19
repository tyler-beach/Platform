const e=`# Evaluation corpus guide

**Status:** Synthetic starter corpus; labels and cases require review before serving as an approved quality baseline. No proprietary code or real customer data belongs in these fixtures.

## Purpose

The platform can produce a plausible but incorrect deviation, apply an irrelevant ADR, cite nonexistent evidence, or fail to abstain when information is missing. This corpus gives reviewers and future implementations fixed inputs and expected dispositions before the assessment pipeline exists.

The corpus is deliberately small and human-readable. It is test data, not executable application code and not a report of model performance.

## Corpus rules

Every case must have:

1. Stable ID and short title.
2. Comparison mode and synthetic source artifacts.
3. Explicit artifact/version identities and evidence locators for any expected citation.
4. Expected disposition and applicability result.
5. Evidence that is acceptable, evidence that would be invalid, and rationale.
6. Whether human review is required.
7. A review state: draft, reviewed, or retired, plus a reviewer/date when approved.

Do not use an unreviewed generated answer as the expected label for the model being evaluated. Labels should be independently reviewed against the source fixture and project policy.

## Core outcome labels

- **Supported deviation:** applicable accepted decision plus source-backed contradiction.
- **No deviation found:** the available and sufficient evidence does not establish a conflict within the defined scope. This is not a universal proof of compliance.
- **Inconclusive:** applicability, source evidence, freshness or semantic resolution is insufficient for a defensible conclusion.
- **Not applicable:** a candidate decision does not govern the analyzed artifact/scope. Preserve this as applicability metadata; do not relabel it a deviation merely because text is similar.
- **Technical failure:** analysis could not complete due to an operational/contract error. Keep this distinct from a finding outcome.

Keep outcome, severity, reviewer disposition, model confidence/quality and execution state as separate fields.

## Suggested directory conventions for future growth

Store each case as Markdown or another simple reviewable text fixture, avoiding executable payloads where possible. If machine-readable fixtures are added later, define a schema and validation before relying on them in CI. Keep source text bounded, synthetic and free of secrets.

Recommended filename: EVAL-###-short-name.md. Do not silently edit a label: record the reason, reviewer and corpus version, especially if prior releases were scored against it.

## Coverage checklist

- [x] Clear deviation
- [x] Similar-looking non-deviation
- [x] Out-of-scope decision
- [x] Insufficient evidence / abstention
- [x] Prompt injection in untrusted source
- [x] Fabricated or wrong-version evidence citation
- [ ] Exception/waiver and supersession
- [ ] Multiple conflicting applicable decisions
- [ ] Stale-source publication race
- [ ] Duplicate delivery/idempotency
- [ ] Malformed model output / schema mismatch
- [ ] Budget exhaustion and ambiguous provider usage
- [ ] Parser limits and hostile document structure
- [ ] Cross-workspace unauthorized reference
- [ ] Renamed/moved source locator

## Scoring protocol to approve before using as a gate

For each corpus revision, report at minimum:

- Outcome classification against acceptable labels.
- Applicability correctness.
- Evidence reference resolution and source-version correctness.
- Reviewer-rated evidence support and unsupported-claim rate.
- Correct inconclusive/abstention rate.
- False-positive and false-negative counts, grouped by case type.
- Cost, model-call count and latency where actual runtime measurements exist.

Do not invent precision/recall targets before there is a representative labeled set and a human review process. Any gate needs an owner-approved threshold, acceptable override behavior, and the corpus/model/prompt/schema versions used to calculate it.

## Starter cases

See [Starter evaluation corpus](STARTER_CORPUS.md). Cases are draft until the expected labels have been reviewed by a human.
`;export{e as default};
