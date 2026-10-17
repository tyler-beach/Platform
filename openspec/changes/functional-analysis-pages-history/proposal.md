# Proposal: Include the functional analysis workflow in the Pages run explorer

## Why

The current Pages explorer's Actions history omits the newer Tree-sitter Functional Analysis Demo workflow. That leaves the primary workflow documented at `docs/functional-analysis-demo.md` absent from the real run timeline and makes the demo site incomplete after runs.

## What changes

- Include `functional-analysis-demo.yml` in the bounded Actions history collector.
- Trigger the documentation refresh after that workflow completes on the default branch, while retaining pull-request exclusion.
- Continue projecting only run/job/step status metadata and trusted repository-scoped run links; do not download workflow artifacts or publish source excerpts through this history path.

## Scope and non-goals

This change adds status history for the functional analysis workflow to the existing internal Pages run explorer. It does not publish its downloadable artifact, change analyzer behavior, enable real-data export, or relax the organization/private-or-internal/Pages visibility gate.

## Acceptance criteria

- The collector requests the functional-analysis-demo workflow, retrieves its jobs for validated numeric run IDs, and emits bounded status metadata.
- The documentation workflow refreshes after eligible default-branch completions of this workflow and does not run for its pull-request executions.
- Tests prove workflow inclusion, bounded projection, and that source/artifact payloads are not copied.
- Existing synthetic Pages fixture remains available when real history export is disabled.

## Risks and rollback

The Pages workflow makes additional read-only Actions API requests. The collector already bounds runs and steps; rollback is removing the workflow from its allowlist and trigger list. Real run-history export remains gated and is not enabled by this change.

## Decisions needing review

None. This follows the existing opt-in Pages policy and exposes only workflow status metadata.
