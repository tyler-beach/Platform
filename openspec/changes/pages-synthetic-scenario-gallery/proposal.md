# Pages synthetic scenario gallery

## Outcome

Turn the Pages walkthrough into a reusable demo surface with a checked-in, generated catalog of synthetic analysis scenarios and recent successful runs of the synthetic Functional Analysis workflow. Visitors can select scenarios across code-diff, technical-spec, and spec-versus-implementation comparisons, inspect exact input files side by side, and review the deterministic analysis, evidence, mock result, and validation output.

## Scope

- Generate a bounded gallery from the existing synthetic Functional Analysis fixtures and deterministic workflow stages.
- Publish the gallery JSON with the Pages build, independent of Actions history and CSV ledger opt-ins.
- Import up to ten recent successful default-branch `workflow_dispatch` Functional Analysis artifacts, validating run identity, artifact digest, input hashes, evidence, and synthetic fixture provenance before publication.
- Render a scenario selector, input panes, source hashes, outcome, evidence references, stage summaries, and validation checks.
- Preserve the current animated walkthrough and workflow run history as separate views.

## Non-goals

- Do not import artifacts from workflows other than Functional Analysis Demo, pull requests, non-default branches, or non-`workflow_dispatch` events.
- Do not use CSV ledger rows or general repository history as source content.
- Do not add live provider calls, secrets, new analysis semantics, or calibrated confidence claims.
- Do not treat the curated gallery as a chronological record of arbitrary workflow-dispatch runs.

## Acceptance criteria

- The generated static catalog contains all nine combinations of the three supported comparison modes and three sample cases.
- The Pages build can add up to ten most recent eligible Functional Analysis workflow artifacts from the preceding 13 days; expired, invalid, or ineligible artifacts are excluded and counted.
- Every case executes the same deterministic prepare, analysis, evidence, budget, mock, and validation stages used by the Functional Analysis workflow; its candidate matches the expected fixture case and all validation checks pass.
- Each catalog input is read only from the approved synthetic fixture tree, carries a SHA-256 digest, and is rendered as escaped text in the browser.
- Selecting a case displays its relevant ADR, technical specification, implementation, and diff panes in a responsive side-by-side layout, along with outcome, evidence, and check details.
- The curated gallery builds and works when Actions history and detailed CSV export are disabled; live artifact entries use an independent read-only Actions API path.
- Browser and build tests reject malformed catalog data and verify the expected scenario set and input digests.

## Risks and rollback

Embedding source text increases the published site size and exposes fixture contents. The importer is limited to the explicitly synthetic workflow, default-branch dispatches, a bounded recent window, exact expected fixture paths, and small validated artifacts. The repository and Pages site are public, so all gallery inputs must remain synthetic. Rollback removes live artifact import and/or the gallery section; the existing walkthrough and run-history features remain available.

## Open decisions

None. Gallery fixtures are explicitly synthetic and already used by the public demonstration workflow.
