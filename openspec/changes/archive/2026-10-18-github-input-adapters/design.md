# Design: GitHub input adapters

## Context

Depends on Go Pathfinder runtime and staged Actions. This change only expands **intake** input shapes.

## Adapter model

```text
Issue body
  → detect mode: package_json | paste_sections | pr_ref | file_bundle
  → adapter.resolve(ctx) → EvidencePackage (pinned) | ValidationError
  → existing ensure-observations → evaluate → publish
```

### PR ref adapter

- Parse GitHub PR URL or `owner/repo#123` limited to `github.repository` unless `cross_repo_attestation` checkbox is set **and** repo is in allowlist env `PATHFINDER_ALLOW_REPOS` (comma-separated). Default: same repo only.
- Resolve PR head SHA via API; pin `revision` on all code artifacts to that SHA.
- Fetch changed files (text only) up to file count and byte caps; skip binaries.
- Optional domain filter unchanged.

### File bundle adapter

- Issue sections listing paths + fenced file contents (already partially paste) OR paths-only + PR/ref to fetch.
- Paths-only without resolvable ref → fail closed.

### Security

- Content is untrusted data.
- Size caps shared with go-pathfinder-runtime.
- No workflow expression embedding of file bodies.
- Fork PRs: require attestation that content is public/synthetic **and** same-repo or allowlist; otherwise reject.

## Open questions resolved

- Cross-repo: allowlist only, default off.
- Binary files: skip with limitation note in report extraction metadata, not silent success.
