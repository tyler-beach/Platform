# ADR pack import tool

Prepare **your** ADRs for Pathfinder testing.

1. **validate** / **scaffold** / **build** — offline, no model.
2. **suggest** — optional Claude drafts for incomplete sidecars (budgeted).

Claude never auto-approves. Treat every suggestion as a review checklist.

## Offline flow

```bash
python3 -m tools.adr_pack validate path/to/adrs

python3 -m tools.adr_pack scaffold path/to/adrs \
  --predicates data/adr_catalog/predicates.json

# humans complete/approve .md.req.json sidecars…

python3 -m tools.adr_pack build path/to/adrs \
  --out path/to/out-catalog \
  --base-predicates data/adr_catalog/predicates.json \
  --catalog-id my-company-pilot
```

## Optional Claude assist (local Claude Code — no API key)

If you use **Claude Code** on your machine (subscription login) but do **not** have `ANTHROPIC_API_KEY`, use the default `--via claude-cli` path. It shells out to `claude -p` with your existing CLI auth.

```bash
# 1) Ensure Claude Code works interactively once
claude -p "ping" --output-format text

# 2) Scaffold offline
python3 -m tools.adr_pack scaffold path/to/adrs \
  --predicates data/adr_catalog/predicates.json

# 3) Plan (no Claude calls)
python3 -m tools.adr_pack suggest path/to/adrs \
  --predicates data/adr_catalog/predicates.json \
  --via claude-cli \
  --max-calls 5

# 4) Execute against Claude Code (still never auto-approves)
python3 -m tools.adr_pack suggest path/to/adrs \
  --predicates data/adr_catalog/predicates.json \
  --via claude-cli \
  --max-calls 5 \
  --execute --yes
```

Optional: `CLAUDE_CLI=/path/to/claude`, `CLAUDE_CLI_MODEL=haiku`, or `--claude-bin` / `--model`.

### Direct Anthropic API (optional)

Only if you have an API key:

```bash
export ANTHROPIC_API_KEY=…
python3 -m tools.adr_pack suggest path/to/adrs \
  --via api --max-calls 5 --execute --yes
```

### Spend / usage controls

| Control | Default | Purpose |
|---|---|---|
| dry-run (no `--execute`) | on | Count eligible ADRs; zero Claude calls |
| `--yes` with `--execute` | required | Explicit confirmation |
| `--via claude-cli` | default | Uses Claude Code login, not API key |
| `--max-calls` | 10 | Hard cap on Claude invocations |
| cache | on | `.adr_pack_cache/` by content hash |
| skip complete | on | Skips approved or filled kind+predicate+subject |
| prompt shape | Decision + metadata | Not the full ADR file |

CLI mode runs `claude` in an empty temp directory and denies common tools so it answers the JSON draft instead of browsing your repo.

## Sidecar fields to complete

| Field | Required for build |
|---|---|
| `kind` | yes |
| `predicate` | yes |
| `subject` | yes |
| `domain` + `applicability.domains` | yes |
| `decision` | yes |
| `approval_state` | must be `approved` |
| `label_status` | must **not** remain `needs_human_typing` |

## Tests

```bash
python3 -m unittest tools.adr_pack.tests.test_adr_pack -v
```
