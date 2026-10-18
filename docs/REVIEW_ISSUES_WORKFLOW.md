# GitHub Issues as the interim human-review workflow

GitHub Issues can be the first review queue while Pathfinder's own queue and transactional review store do not exist. An issue is a coordination/audit pointer—not the source of truth for the original machine finding and not an automatic training signal.

## Current demo integration

The **Functional Analysis Demo** workflow gains an opt-in `Create a GitHub review issue` input (off by default). When enabled, after the selected synthetic scenario passes validation, the workflow creates one issue containing:
- run URL and attempt, comparison/scenario, original outcome and validation status;
- immutable artifact version references and evidence IDs/locators;
- validation checklist and the exact feedback format;
- explicit warning that the current demo uses synthetic fixtures and a deterministic mock model.

The helper posts references/metadata only; it does not copy source excerpts, prompts, secrets, or the full evidence package. The workflow uses the repository-scoped `GITHUB_TOKEN` with `issues: write`. It does not run for pull-request events or automatically create issues on every run. This is a demonstration integration; the production deviation detector is not yet connected.

## Reviewer process

1. Open the issue and inspect the linked run artifact plus the original ADR/requirement and pinned source revision.
2. Add a comment using the YAML response block in the issue. Choose a controlled disposition and reason code, cite supporting and contradicting evidence IDs, and select the feedback route.
3. Use `needs_adjudication: true` for high-impact, disputed, or policy-sensitive decisions. Do not close the issue as a proxy for silently changing the machine result.
4. An adjudicator records a separate adjudication event. Only approved, adjudicated candidate feedback can be exported by `.poc/review_sampling/promote_review_feedback.py`; that export never modifies the baseline corpus.
5. Turn a candidate into a reproducible evaluation case, run regression/slice metrics, and review the release separately. Holdout cases are never tuning inputs.

## Issue states and labels

For now, the issue itself is the queue. Use the title prefix `[Pathfinder review]`; issue comments carry reviewer dispositions. Suggested labels, if created in repository settings, are `pathfinder-review`, `needs-adjudication`, `feedback-candidate`, `false-positive`, `missed-deviation`, and `needs-evidence`. Labels are workflow convenience only, not ground truth.

## Limits and privacy

The repository is public. Never post proprietary code, customer information, secrets, credentials, raw prompts, or sensitive evidence excerpts in issues. Keep immutable evidence in the controlled artifact/evidence store and put only approved references in the issue. A public GitHub issue is not suitable for confidential production evidence.

Issues/comments are editable, so they are not a substitute for the append-only hash-chained review-event ledger. Before production use, mirror accepted dispositions into a durable append-only event store with authenticated reviewer identity, authorization, timestamps, analysis version, reason code and evidence refs. Issue closure must not auto-close findings, waive ADRs, retrain models, or promote evaluation labels.

## Manual form

Use the repository's `Pathfinder finding review` issue form for manually submitted review packets. The generated issue body uses the same fields in a comment template because GitHub Issue Forms only apply when creating an issue, not when responding to a pre-created issue.
