const e=`# Human review sampling and feedback loop

**Status:** Design proposal for Pathfinder. This describes a review-control design; it does not claim a production review queue or feedback service is deployed.

## Goals

1. Estimate quality across all analysis outcomes, not only findings the system already considers actionable.
2. Catch false negatives, overconfident findings, wrong-ADR matches, weak evidence and systematic collector blind spots.
3. Convert reviewer decisions into versioned, attributable evaluation signals without silently changing past analyses or allowing one reviewer to retrain production behavior.
4. Keep operational review decisions separate from ground-truth labels used for evaluation.

## Two queues, not one

Maintain two independently budgeted review streams:

- **Probability sample (quality measurement):** randomly sample eligible analysis units from a defined population. This is the source for estimates of false-positive/false-negative rates and reviewer agreement. It must include aligned/no-deviation and inconclusive outcomes, not just findings.
- **Risk/learning sample (diagnosis):** deliberately oversample high-impact, novel, low-evidence, disputed, stale, approximate, unresolved, and policy-sensitive cases. Use it to find failure modes and improve the pipeline, but do not mix it unweighted into population-level quality estimates.

A case can enter either or both queues, but the sample reason and inclusion probability must be recorded. The risk queue is not a random sample and must never be presented as representative quality measurement.

## What is the sampling unit?

Use the **requirement × analyzed artifact snapshot × analysis run** as the default unit, not each evidence span. This avoids inflating sample counts when one finding contains many spans and permits sampling aligned cases where no finding exists. When multiple findings refer to the same requirement/run, group them into one review packet and expose all relevant evidence and counter-evidence. If the operational question is specifically evidence-locator quality, define a separate evidence-span sampling frame.

The sampling frame must be explicit and immutable for each batch: workspace/tenant, repositories, date window, pipeline and schema versions, eligible terminal outcomes, and exclusions. Store a hash/count of the frame and a snapshot reference. Never silently omit failed or inconclusive analyses; report exclusions and missing strata.

## Initial sampling policy

Start with a small, explainable policy and tune only after measuring reviewer capacity:

1. Build a deduplicated frame of eligible terminal requirement assessments.
2. Partition by outcome (deviation, no-deviation, potential, inconclusive), severity/impact where applicable, and evidence-strength band. Keep strata bounded; do not create tiny cells for every model/repository combination.
3. Draw a seeded random sample within each stratum, with a minimum floor for rare but important outcomes and a maximum total review budget.
4. Keep the inclusion probability for every sampled unit. If the draw uses different sampling rates by stratum, use inverse-probability weights for aggregate estimates.
5. Add a separate risk queue based on explicit triggers such as unresolved/approximate source mapping, stale or mismatched evidence, weak or absent normative requirement, conflict between supporting and contradicting evidence, new parser/model/prompt version, reviewer disagreement, and high-impact security decisions.
6. Cap duplicate work: avoid repeatedly sampling the same requirement/artifact snapshot unless a follow-up is intentionally measuring reproducibility. Re-sample new revisions as new units.
7. Persist the batch seed, policy version, frame fingerprint, strata counts, selection reason, inclusion probability, selected time, and reviewer assignment. A seed supports reproducibility; it is not a substitute for storing the actual selected IDs.

Do not treat the current evidence-strength score as a probability that a finding is correct. It can be a stratum or risk signal only.

## Human review packet

A reviewer packet should show, in this order:

- exact normative requirement and decision ID/version/status/applicability basis;
- analyzed source/config/spec revision and digest, plus locator precision and authorized excerpt;
- source observation(s), collector/resolver version, and whether each is direct, approximate, unresolved or runtime-derived;
- supporting **and** contradicting evidence, each linked to the claim it bears on;
- machine outcome, rationale, evidence-strength components and validation results (not a pseudo-probability);
- known limits: reachability, deployment binding, environment, refresh/override paths, unsupported formats and missing evidence;
- separate reviewer action and structured reason.

Do not ask reviewers to approve a model explanation in the abstract. Ask them to judge the requirement's applicability, whether the cited observation is accurate, whether the inference follows, what evidence is missing, and what disposition is warranted.

## Disposition taxonomy

Keep the machine assessment outcome immutable. Append a separate review event with:

- **confirmed_deviation** — cited evidence and scope support a real deviation;
- **false_positive** — the claim does not hold; require a reason code such as wrong ADR, out of scope, valid exception, incorrect observation, or invalid inference;
- **aligned_confirmed** — sampled no-deviation result is supported by the evidence examined;
- **missed_deviation** — reviewer finds a deviation in a case the system marked aligned/no deviation;
- **inconclusive_correct** — evidence really is insufficient;
- **needs_more_evidence** — identify the missing artifact, runtime fact, decision clarification or source mapping;
- **cannot_review** — access, stale snapshot, missing source, or conflict of interest prevents a valid judgment.

The disposition is not ground truth automatically. Record reviewer identity/role, timestamp, rationale, reason code, evidence references, requirement/decision version, source snapshot, batch ID, and any follow-up ticket. For high-impact or disputed cases, require a second independent reviewer or adjudicator. Preserve the original and each subsequent disposition append-only.

## Feedback loops: improve the right component

Route each review event to a typed feedback destination; do not dump all feedback into a single prompt or generic model memory.

| Reviewer signal | First destination | Safe next action |
|---|---|---|
| Wrong ADR / requirement out of scope | Applicability/retrieval evaluation | Add a labeled retrieval case; inspect metadata filters, lifecycle state, and chunking |
| Correct ADR, missed relevant requirement | Retrieval recall evaluation | Add a missed-match case; review query construction and top-k/filters |
| Source locator wrong or stale | Collector and provenance tests | Add regression fixture for path/span/hash/version; fix mapping before semantic tuning |
| Observation accurate, inference wrong | Deterministic rule/model evaluation corpus | Add a counterexample with expected outcome and reviewer rationale |
| Missing counter-evidence | Evidence retrieval/selection | Add an evidence-recall case and test balanced retrieval |
| Outcome too strong for evidence | Validation/guardrail policy | Tighten downgrade/escalation conditions; never use a score threshold as the only gate |
| Valid exception or conflicting decision | ADR lifecycle/exception model | Fix decision metadata or exception handling; do not teach model to ignore the rule globally |
| Runtime/deployment context missing | Evidence acquisition backlog | Add a typed unresolved requirement for runtime/deployment evidence |
| Consistent reviewer disagreement | Adjudication queue | Compare independent reviewers and clarify policy before using labels for tuning |

### Promotion lifecycle

1. Store the review event as an immutable record linked to the original run and input fingerprints.
2. Normalize it into a candidate evaluation case with reviewer rationale and exact expected evidence/decision links.
3. Require review of sensitive source data and a second adjudication for high-impact labels or disagreements.
4. Add the case to a versioned offline corpus. Keep reviewer labels, adjudication status, and provenance.
5. Run regression metrics and slice analysis against the prior corpus; compare precision/recall, false-positive/negative categories, evidence correctness, inconclusive escalation, and reviewer agreement.
6. Promote only through a reviewed change to retrieval/rules/prompt/model configuration with versioned release notes and a rollback path. Never update a live prompt/model from one review event.
7. Keep holdout cases out of tuning. Otherwise the dashboard can improve by memorizing reviewed examples.

## Avoid biased estimates

- Do not sample only high-confidence findings; this misses false negatives and incorrect aligned decisions.
- Do not treat the risk queue as a probability sample.
- Track nonresponse and cannot-review rates by stratum; adjust estimates or report the bias when reviewers skip cases.
- Use independent double-review on a subset to estimate reviewer agreement and adjudicate disagreement.
- Report weighted metrics with confidence intervals where sample sizes support them. A small pilot sample should show counts and uncertainty, not falsely precise percentages.
- Keep repository, language, artifact type, pipeline version, and outcome slices for diagnosis, while avoiding high-cardinality dashboard labels.
- Separate repeated versions of one source from independent samples; cluster uncertainty by repository or requirement when appropriate.
- Never tune the threshold to maximize apparent accuracy on the same cases used to tune it.

## Minimal data model

Suggested logical records (names illustrative; align them with the authoritative Protobuf/database contract before production):

- **ReviewBatch:** batch ID, policy version, created time, population window/scope, frame fingerprint/count, seed, strata, selected IDs, inclusion probabilities.
- **ReviewAssignment:** unit ID, reviewer ID/role, assigned/due/completed times, status, skip reason.
- **ReviewEvent:** append-only disposition, reason code, rationale, evidence links, actor, occurred time, original analysis/version fingerprints, supersedes event if corrected.
- **FeedbackCase:** normalized failure mode, affected stage, proposed expected result, source fixture reference, adjudication state, corpus version.
- **EvaluationRelease:** code/rule/prompt/model versions, corpus and holdout fingerprints, metrics by slice, reviewer sign-off, rollout/rollback reference.

Store reviewer rationale and source excerpts under appropriate access controls and retention. Audit events must not include raw prompt dumps or unrestricted source content.

## Metrics and launch gates

Measure sample coverage, response rate, double-review agreement, weighted confirmed-deviation precision, missed-deviation rate among sampled non-deviations, evidence locator correctness, wrong-applicability rate, counter-evidence recall, and the fraction correctly escalated as inconclusive. Report numerator, denominator, uncertainty, strata, frame date, and policy/corpus version.

Start in shadow mode. The first release should only select and route cases, collect review events, and produce offline reports. Do not auto-close findings, auto-waive ADRs, or change a production model based on these labels. Define minimum sample size and confidence requirements with reviewers before using the estimates as release gates.

## Suggested implementation order

1. Define the sampling frame and immutable review-event schema.
2. Build a seeded, stratified sampler and unit tests for reproducibility, inclusion probabilities, duplicate prevention, and rare strata.
3. Add an explicit review queue and append-only disposition endpoint/storage.
4. Export reviewed cases to an offline, versioned evaluation corpus with adjudication status.
5. Add a report comparing pipeline versions and showing false-negative probes from sampled aligned cases.
6. Only after reviewers validate the corpus, use it to tune retrieval/rules/model behavior.

This is the quality-control design. The repository's existing PoC CSV store is single-runner demo persistence, not a production transactional review database; production concurrency, tenant isolation, retention, and reviewer authorization require the platform's real persistence/API implementation.
`;export{e as default};
