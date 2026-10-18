# Design: GitHub Actions Go Pathfinder runtime

## Context

Today: one Actions job runs `python .poc/issue_analyze/issue_package.py` end-to-end. Target: Go owns brains; Actions owns staged orchestration (stand-in for future SFN/workers). No AWS in this phase.

## Goals / Non-Goals

**Goals:** deterministic Go core; CLI parity; staged Actions; fail-closed validation; no source echo in comments; reproducible fingerprints.

**Non-goals:** cloud services; model assessment; PR/file remote adapters (companion change); retiring all Python at once.

## Architecture

```text
Issue event
  → workflow pathfinder-issue-analyze (orchestrator)
      → job/call: intake        (fetch issue → package.json | error comment.md)
      → job/call: ensure-obs    (paste extract if needed → package.json)
      → job/call: evaluate      (catalog evaluate → report.json)
      → job/call: publish       (comment.md + gh comment + artifact upload)
```

Each stage is a reusable workflow (`workflow_call`) or job with artifact handoff. Stage inputs are artifact paths + small JSON metadata (issue number, run URL, repo). Large source stays in work-dir artifacts, not in workflow expressions.

### Go layout

```text
go/pathfinder/
  go.mod   # module github.com/tyler-beach/Platform/go/pathfinder
  internal/engine
  internal/predicates
  internal/catalog
  internal/normalize
  internal/collect/package
  internal/extract/paste
  internal/evaluate
  internal/issueintake
  cmd/pathfinder-issue-analyze
  cmd/pathfinder-evaluate-package
```

Functional core: `engine`, `normalize`, kind evaluation, fingerprint/canonical — pure over values. Shell: CLI, filesystem, `gh` exec for issue fetch/comment.

### Parity contract

Preserve:

| Item | Value |
|------|--------|
| Engine version | `generic-requirement-engine-v3` (bump only with intentional contract change + tests) |
| Package schema | `pathfinder-evidence-package-v1` |
| Report schema | `pathfinder-package-evaluation-v1` |
| Extractor | `paste_heuristic_v1` / `paste-heuristic-v2` |
| Exit | success JSON stdout; failure JSON stderr + exit 2; `comment.md` always written when `--comment` or failure path requires it |
| Artifacts | `package.json`, `report.json`, `comment.md` |

### Orchestration simulation (Actions ≈ SFN)

| SFN concept | Actions stand-in |
|-------------|------------------|
| State machine | Parent workflow + ordered jobs / `workflow_call` chain |
| Task worker | Job step running one Go command |
| State payload | Artifacts + output parameters (IDs, hashes, status only) |
| Idempotency | `concurrency` group per issue; publish stage upserts/replaces Pathfinder comment marker rather than flooding |
| Retry | Job/`continue-on-error` policy only where classified retryable; intake validation failures are terminal |
| Observability | Step summaries + artifact retention; no full source in logs |

### Decisions

1. **Catalog stays under `.poc/requirement_catalog/`** for this change to avoid dual data roots; a later change may move to `data/requirement_catalog/`.
2. **Single binary can expose subcommands** later; first ship two cmds for clarity and workflow readability.
3. **Python remains in-repo as oracle** until Go parity suite green; production workflow must not call it.
4. **Comment idempotency:** publish looks for an existing comment containing a stable marker (`<!-- pathfinder-analyze-report -->`) and updates via API when present; otherwise creates. Prevents edit-storm duplicates under at-least-once runs.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Paste extractor behavioral drift | Golden fixtures from `.poc/issue_analyze/fixtures` + side-by-side oracle tests |
| Go JSON key ordering / float edge cases | Canonical `json.Marshal` with sorted keys helper matching Python `separators=(",", ":")` + `sort_keys` |
| Actions artifact race / missing file | Stages fail closed if required artifact absent; publish still emits error comment when possible |
| Monolithic Go CLI recreates Python blob | Packages enforce core vs shell; stages invoke narrow commands (`ensure-observations`, `evaluate`, `render-comment`) |
| Secret leakage via `gh` / logs | Never log package bodies; comment redaction tests |

## Migration plan

1. Go engine + evaluate_package parity (unit).
2. Paste + issue intake parity (fixture).
3. Monolithic Go CLI behind workflow feature flag / branch workflow.
4. Split reusable stage workflows; switch production workflow.
5. Remove Python from production workflow; leave `.poc` reference until archive of retirement change.

## Open questions (resolved)

See `DECISIONS.md` (grill-me rounds). Summary: Actions+portable Go; `pathfinder-jobs` ledger in M1; Python oracle retained; M2 = same-repo PR changed-files only; advisory synthetic catalog; no AWS deploy in this phase.
