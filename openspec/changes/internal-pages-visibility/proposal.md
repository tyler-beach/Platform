# Proposal: Allow private Pages exports from internal organization repositories

## Why

The Pages exporter currently allows real run data only when repository visibility is exactly `private`. GitHub Enterprise Cloud also supports privately published project Pages from organization-owned `internal` repositories. This rejects the intended internal-only repository setup even when Pages access itself is confirmed private.

## What changes

- Permit real-data export from organization-owned repositories with visibility `private` or `internal`.
- Continue requiring the Pages API to report `public: false` and `PAGES_REAL_RUN_DATA_ENABLED` to equal exactly `true`.
- Reject personal repositories and all public repositories when real-data mode is enabled.
- Update the workflow gate, tests, and operator-facing wording.

## Scope and non-goals

This does not publish data from a public Pages site, relax the exact opt-in, change pull-request exclusions, or add credentials to the browser. It only aligns the repository gate with GitHub's supported organization repository visibility options for private Pages.

## Acceptance criteria

- `private` and `internal` organization repositories pass only when Pages is confirmed `public: false` and opt-in is exact `true`.
- A public repository, a user-owned repository, a public/unknown Pages response, or a missing opt-in does not export ledger data.
- Workflow invocation passes the repository owner's type to the pure visibility guard.

## Risks and rollback

GitHub Pages access control requires an eligible GitHub Enterprise Cloud organization. The guard still fails closed when the Pages API cannot confirm private access. Revert the visibility set if actual clone testing shows the Pages API represents internal repositories differently.

## Decisions needing review

None. This implements the user's stated internal-only organization Pages target and retains the existing opt-in and access checks.
