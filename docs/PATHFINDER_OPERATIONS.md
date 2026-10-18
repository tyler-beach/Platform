# Pathfinder operations (GitHub Actions prototype)

## Artifacts

- Workflow artifact name: `pathfinder-issue-evaluation-<run_id>-<attempt>`
- Contents: `report.json`, `comment.md`, `package.json`, `job.json`
- Retention: **14 days** (see `pathfinder-go-analyze.yml`)

## Job ledger

- Branch: `pathfinder-jobs` (machine commits only)
- File: `jobs/jobs.jsonl` (append-only lean records)
- Soft-fail: evaluate comment/artifacts are kept if ledger push fails after retries

## Catalog modes

| Mode | Pack | How to select |
|---|---|---|
| `real` (default) | `data/adr_catalog` | omit flag/env, or issue **Catalog pack** = Real |
| `synthetic` | `.poc/requirement_catalog` | `--catalog-mode=synthetic`, `PATHFINDER_CATALOG=synthetic`, or issue dropdown |

Regenerate real pack: `python3 data/adr_catalog/generate_pack.py`

## Model extract (optional, off)

`PATHFINDER_ENABLE_MODEL_EXTRACT=1` is reserved. Without `ANTHROPIC_API_KEY` it fails closed. Default CI/Actions paths use deterministic paste extraction only.

## Re-run / support

- Re-run: workflow_dispatch with issue number
- Docs: `PATHFINDER_FIRST_RUN.md`, `ISSUE_ANALYZE_WORKFLOW.md`
- Findings are advisory; no merge blocking
