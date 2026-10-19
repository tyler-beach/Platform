# Design: ADR pack import tool

## Approach

Treat company ADR markdown as **source artifacts** and typed sidecars as the **governed pack input**. The tool never calls a model.

```text
adrs/*.md  --validate--> structure report
         \-scaffold--> adrs/*.md.req.json  (draft, needs_human_typing)
         \-build-----> requirements.jsonl + predicates.json + catalog_manifest.json
                              (only complete + approved sidecars)
```

## Sidecar schema (v1)

JSON next to each ADR: `ADR-….md` → `ADR-….md.req.json` (stdlib JSON; no model, no PyYAML required).

Required for build: `adr_id`, `requirement_id`, `title`, `domain`, `lifecycle_status`, `kind`, `predicate`, `subject`, `decision`, `approval_state=approved`, `applicability.domains`.

Optional: `limit`, `approved_set`, `forbidden`, `applicability.languages`, `label_status`.

## Heuristics (suggest only)

Regex over the Decision section for `MUST NOT exceed N`, `at least N`, bare `MUST` → candidate `kind`/`limit`. Predicate suggestion only by matching known registry keys or a slug from the title; always `suggestion_source=heuristic` and never approval.

## Optional Claude assist

Command: `python3 -m tools.adr_pack suggest` (separate from offline scaffold).

Provider: local Claude Code CLI only (`claude -p` + subscription login). No in-process Anthropic HTTPS client and no `ANTHROPIC_API_KEY` requirement.

Controls:
- Default dry-run; live path requires `--execute --yes`
- Budgets: `--max-calls` (default 10), cumulative input/output estimate caps
- Skip approved and already-complete (kind+predicate+subject) sidecars
- Content-hash cache under `adrs/.adr_pack_cache/` (gitignored)
- Prompt sends title/domain/status + truncated Decision + known predicate ids only
- Empty temp cwd + disallowed tools; default model alias `haiku`
- Merge fills empty fields only; forces `approval_state=draft`

## Layout

- `tools/adr_pack/` package + `__main__.py`
- Tests under `tools/adr_pack/tests/`
- Docs pointer in `data/adr_catalog/README.md` and `tools/adr_pack/README.md`
