# Proposal: GitHub input adapters (M2)

## Why

M1 delivers Go evaluate on issue paste/package. Phase success (unaided collaborator) also needs same-repo **PR changed-files** intake so multi-file code reaches the package without issue zip/bundles.

## What Changes

- Go intake adapter: parse same-repo PR URL/number from the issue; reject forks and cross-repo refs.
- Fetch changed text files at PR head SHA within caps; skip denylisted secret-ish paths (limitations, not hard-fail).
- Pin code artifacts to head SHA; tech-spec optional; hand off to existing ensure→evaluate→publish→ledger.
- Issue form: add optional PR field; keep single sample-code field (no multi-file issue bundles).

## Capabilities

### New Capabilities
- `analyze-input-adapters`: Same-repo PR → pinned evidence package on Actions.

### Modified Capabilities
- `issue-package-evaluation`: Intake accepts adapter-resolved PR packages in addition to inline package/paste.

## Non-goals

- Fork PRs, cross-repo without future allowlist, entire head tree fetch, issue zip/multi-fence bundles, AWS, real ADR store, merge blocking

## Depends on

- M1 `github-actions-go-pathfinder` merged (Go runtime, ledger, staged workflow)
