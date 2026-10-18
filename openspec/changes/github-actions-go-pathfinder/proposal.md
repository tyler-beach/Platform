# Proposal: GitHub Actions Go Pathfinder runtime (M1)

## Why

The Pathfinder analyze loop works on GitHub Issues, but evaluation brains live in Python. Project direction is Go. This milestone makes GitHub Actions a **production-usable** runtime for collaborators in a single trusted repo, with contracts portable to a later AWS shell. AWS deploy remains out of scope.

## What Changes

- Go module owns the shared evaluation spine and issue-analyze CLI (schema/CLI parity with today’s Python path).
- Production `pathfinder-issue-analyze` uses Go + staged reusable Actions only; Python `.poc` remains an **offline oracle**, never the production entrypoint.
- Durable **job ledger**: append-only JSONL on branch `pathfinder-jobs` (lean index; full report in Actions artifacts).
- Comment publish with stable marker (update-in-place); ledger soft-fail with retry if comment already succeeded.
- Catalog stays synthetic (`synthetic_unadjudicated`); findings advisory only (no merge blocking).

## Capabilities

### New Capabilities
- `go-pathfinder-runtime`: Go evaluation core + issue-analyze CLI.
- `actions-stage-orchestration`: Staged Actions orchestration and artifact handoff.
- `pathfinder-job-ledger`: Append-only job index on `pathfinder-jobs` with serialized writes + retry.

### Modified Capabilities
- `issue-package-evaluation`: Production path MUST be Go staged Actions; MUST NOT invoke Python evaluate entrypoints.

## Non-goals (M1)

- PR URL / multi-file adapters (**M2**: `github-input-adapters`)
- AWS services, multi-tenant control plane, real ADR store, model calls, merge blocking
- Deleting Python `.poc` oracle
- Issue multi-file bundles (multi-file is PR-only in M2)

## Acceptance criteria

- OpenSpec validates; grill decisions in `DECISIONS.md` reflected in specs.
- Go tests + local fixture dry-run green.
- Workflow on main uses Go only; posts/updates comment; attempts ledger append.
- Q10 (unaided outsider) is **not** claimed until M2.
