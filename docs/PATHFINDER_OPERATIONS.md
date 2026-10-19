# Pathfinder operations (GitHub Actions prototype)

## Artifacts

- Workflow artifact name: `pathfinder-issue-evaluation-<run_id>-<attempt>`
- Contents: `report.json`, `comment.md`, `package.json`, `job.json`
- Retention: **14 days** (see `pathfinder-go-analyze.yml`)

## Job ledger

- Branch: `pathfinder-jobs` (machine commits only)
- File: `jobs/jobs.jsonl` (append-only lean records)
- Aggregate: `dashboard/summary.json` (90-day operational projection, regenerated with each ledger commit)
- Soft-fail: evaluate comment/artifacts are kept if ledger push fails after retries

## Usage dashboard and OpenTelemetry

- Pages route: `/usage`; it fetches the aggregate from the public `pathfinder-jobs` branch and refreshes every five minutes while open. Analysis updates do not redeploy the Pages site.
- Data scope: job counts, allowlisted package statuses/requirement outcomes, and fixed-stage run/error/skipped/duration aggregates. No raw traces or issue/run identifiers are placed in the dashboard projection. The Pages site and data branch must both be public for anonymous browser reads.
- Stage telemetry comes from measured Go instrumentation and is present even if no external OTLP endpoint is configured. The projection updates in the same serialized ledger write and Pages refreshes it without a Pages redeployment.
- Optional OTLP/HTTP export: set Actions variable `OTEL_EXPORTER_OTLP_ENDPOINT` and, when needed, secret `OTEL_EXPORTER_OTLP_HEADERS`. No endpoint means no telemetry export. Export failure does not fail analysis.
- The current workflow makes no model call. AI token and spend data are unavailable, not zero.
- Full design, privacy limits, and migration implications: `PATHFINDER_USAGE_DASHBOARD.md`.

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
