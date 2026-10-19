# ADR pack import tool

Prepare **your** ADRs for Pathfinder testing.

1. **validate** / **scaffold** / **build** — offline, no model.
2. **suggest** — optional, budgeted Claude drafts for incomplete sidecars (local testing).

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

## Optional Claude assist (local, budgeted)

Use after `scaffold`, only for sidecars still missing kind/predicate/subject.

```bash
# Plan only — no API spend (default)
python3 -m tools.adr_pack suggest path/to/adrs \
  --predicates data/adr_catalog/predicates.json \
  --max-calls 5

# Spend tokens deliberately (requires key + confirmation)
export ANTHROPIC_API_KEY=…          # local env only; never commit
export ANTHROPIC_MODEL=claude-haiku-4-5   # optional; cheaper default for this tool

python3 -m tools.adr_pack suggest path/to/adrs \
  --predicates data/adr_catalog/predicates.json \
  --max-calls 5 \
  --execute --yes
```

### Spend controls

| Control | Default | Purpose |
|---|---|---|
| dry-run (no `--execute`) | on | Count eligible ADRs; zero Messages calls |
| `--yes` with `--execute` | required | Explicit spend confirmation |
| `--max-calls` | 10 | Hard cap on Messages requests |
| `--max-output-tokens` | 350 | Per-call output cap |
| `--max-input-tokens-total` | 50000 | Session input budget |
| `--max-output-tokens-total` | 4000 | Session output budget |
| cache | on | `.adr_pack_cache/` by content hash; reruns are free |
| skip complete | on | Skips approved or already-filled kind+predicate+subject |
| prompt shape | Decision + metadata | Not the full ADR file; Decision truncated |

Model output is merged into **draft** sidecars only (`approval_state` stays `draft`). You still set `approval_state=approved` after review.

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
| `limit` / `approved_set` | when kind requires them |

## Tests

```bash
python3 -m unittest tools.adr_pack.tests.test_adr_pack -v
```
