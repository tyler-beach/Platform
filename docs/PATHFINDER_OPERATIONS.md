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

## Semantic extraction (optional, off)

Default workflows use deterministic Go extraction only. To opt in, set repository variable `PATHFINDER_ENABLE_MODEL_EXTRACT=true`, set `PATHFINDER_ANTHROPIC_MODEL` to the approved Anthropic model ID, and configure Actions secret `ANTHROPIC_API_KEY`.

The opt-in normalizer accepts candidates only from the loaded catalog and registry, requires one exact quote in a pinned source artifact, and derives evidence ID, hash, revision, path, locator and role in Go. Tech specs are `design_assertion`; code/config/PR content is `implementation_fact`. Both roles share one evidence schema and are evaluated together once per requirement; their roles remain in provenance. The model never decides alignment/deviation.

Per workflow invocation: one exact-request token-count preflight; no generation above 20,000 input tokens; at most one generation request; maximum 4,000 output tokens and 64 evidence facts; 60-second deadline; no retry or repair. Secret-like input detected by the best-effort scanner is skipped before provider transmission. Errors and budget skips are labeled, deterministic evidence may still be evaluated, and missing evidence stays inconclusive. Reports retain safe model/prompt/schema and usage metadata; source bodies and response bodies are not logged. Keep the public/synthetic attestation requirement.

These are per-invocation limits, not an organization spend quota. Every issue edit, dispatch, or rerun can create another bounded invocation, and the workflow does not yet enforce a per-user or monthly budget. Keep semantic extraction disabled on a public repository; before enabling it broadly, restrict who can trigger analysis and add a durable spend/quota control.

Live Anthropic behavior is not exercised by the offline Go suite; run a controlled labeled evaluation before enabling this in a real organization.

The reusable flow remains independent of ADR identity, but the prototype still loads the checked-in catalog and scopes candidate predicates from it. Enterprise-scale ADR retrieval, partitioned catalog loading, and organization-wide usage quotas remain future work; no 50,000-ADR scale claim is established by this prototype.

## Re-run / support

- Re-run: workflow_dispatch with issue number
- Docs: `PATHFINDER_FIRST_RUN.md`, `ISSUE_ANALYZE_WORKFLOW.md`
- Findings are advisory; no merge blocking
