const e=`# Finding review playbook

A Pathfinder result is a review lead backed by specific artifacts—not a verdict about a system. Use this page when reviewing a finding in the demo or shaping the production review workflow.

## Start with the claim, not the label

For each finding, read these fields together:

- **Requirement or decision:** the constraint being checked, including its source revision.
- **Observed behavior:** the concrete code, configuration, document, or change that triggered the comparison.
- **Evidence references:** immutable artifact identity plus a source locator such as a path and line range. A reference tells a reviewer where the observation came from; access to the underlying artifact still needs its own authorization.
- **Reasoning and limits:** why the observation supports the result, what assumptions were made, and what the evidence does *not* establish.
- **Review state:** whether a person has accepted, rejected, or deferred the finding. Review state is not the same thing as the analysis result.

## Interpret the outcome

| Outcome | What it means | Reviewer action |
|---|---|---|
| **Aligned** | Available evidence supports the requirement and the observed implementation is consistent with the decision. | Check that the evidence covers the relevant execution path and current revision. |
| **Deviation supported** | Evidence supports a concrete mismatch between a requirement/decision and an observed implementation or configuration. | Confirm scope and impact; decide whether to remediate, document an exception, or revise the decision. |
| **Potential finding** | A signal deserves investigation, but the evidence does not yet support a definitive deviation. | Gather the missing context, inspect adjacent call paths, or route to the owning team. |
| **Inconclusive** | The available evidence cannot establish alignment or deviation—for example, a required binding, deployment value, or revision is missing. | Record the evidence gap. Do not silently treat unknown as compliant. |

These are outcome categories, not calibrated probabilities. A support score or model explanation must not be presented as the probability that a finding is true.

## A practical review sequence

1. **Pin the inputs.** Verify the ADR/requirement revision, source commit, configuration revision, and any generated artifact version used by the run.
2. **Open the cited spans.** Confirm that the path, line range, symbol, or configuration key points to the claimed observation. If the locator has drifted, re-run against the right revision rather than guessing.
3. **Follow the behavior.** Check callers, data flow, environment-specific values, and runtime controls. A local expression may not determine the effective behavior by itself.
4. **Challenge the inference.** Look for a guard, override, policy, test, or downstream control that changes the conclusion. Distinguish direct observation from an inference made by a rule or model.
5. **Choose a review action.** Accept the finding, reject it with a reason, defer it pending evidence, or create a remediation/exception task. Preserve the reviewer, timestamp, rationale, and input versions.
6. **Keep the result reproducible.** A later run should create a new analysis record tied to its own inputs. Do not rewrite the evidence for an earlier result to make it look current.

## Example: a session TTL requirement

Suppose the requirement says, “An access session MUST have an absolute lifetime no greater than 10 minutes.”

A source observation showing a token expiry computed as \`now + 30 minutes\` is a strong signal, but review still needs to establish that this code path issues the relevant access session, that the duration is not overridden, and that the cited source revision matches the analyzed artifact. A test fixture or a similarly named setting is not enough on its own.

Conversely, finding \`600\` in one configuration file does not prove the end-to-end invariant. Refresh behavior, alternate issuance paths, and effective deployment configuration may matter. If those are absent from the evidence set, the correct result may be **inconclusive**, not aligned.

## Evidence boundaries

Pathfinder should keep these distinctions explicit:

- **Observed:** a parser, rule, API, or collector returned a specific value or source span.
- **Inferred:** a deterministic rule or bounded model connected observations to a requirement.
- **Verified:** a separate check or reviewer validated a claim against stated criteria.
- **Not established:** runtime behavior, reachability, exploitability, or production state that was not actually measured.

A passing static check does not prove runtime behavior. A configuration declaration does not prove that it was deployed. A missing observation does not prove that a control is absent. Model output is untrusted input to the workflow and must not bypass deterministic validation, evidence checks, or human review.

## What to record when closing a finding

A useful review record contains the disposition, rationale, reviewer identity, timestamp, affected requirement/decision version, source revision, evidence references, and any follow-up ticket or approved exception. If the finding was rejected because evidence was incomplete or stale, preserve that reason; it helps improve the collector and the next analysis.

> **Demo note:** the linked walkthroughs and examples use synthetic artifacts and deterministic mock data. They illustrate the intended review model; they are not evidence of a live production scan or a deployed API.
`;export{e as default};
