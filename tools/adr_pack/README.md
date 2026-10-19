# ADR pack import tool

Offline helper to prepare **your** ADRs for Pathfinder testing. **No model calls.**

Pathfinder does not evaluate free-form ADR prose alone. It needs typed requirement rows (kind, predicate, subject, limits, applicability). This tool:

1. **Validates** markdown structure (title, Status/Domain metadata, Decision section).
2. **Scaffolds** draft typed sidecars (`.md.req.json`) with optional heuristic *suggestions*.
3. **Builds** a catalog pack only from sidecars you mark `approval_state: approved` after review.

Heuristics never auto-approve. Treat suggestions as a starting checklist for architecture owners.

## Commands

From the repository root:

```bash
# Lint a directory of ADR markdown files
python3 -m tools.adr_pack validate path/to/adrs

# Create draft sidecars (skips already-approved ones)
python3 -m tools.adr_pack scaffold path/to/adrs \
  --predicates data/adr_catalog/predicates.json

# After humans fill/approve sidecars, emit a pack
python3 -m tools.adr_pack build path/to/adrs \
  --out path/to/out-catalog \
  --base-predicates data/adr_catalog/predicates.json \
  --catalog-id my-company-pilot
```

Point Pathfinder at `--out` as the catalog directory (same layout as `data/adr_catalog`: `requirements.jsonl`, `predicates.json`, `catalog_manifest.json`). Keep ADR markdown available for digest binding; copy or symlink `adrs/` as needed for your pilot layout.

## Sidecar fields to complete

| Field | Required for build |
|---|---|
| `kind` | yes (`numeric_max`, `numeric_min`, `boolean_required`, …) |
| `predicate` | yes (registry id) |
| `subject` | yes |
| `domain` + `applicability.domains` | yes |
| `decision` | yes (usually copied from markdown) |
| `approval_state` | must be `approved` |
| `label_status` | must **not** remain `needs_human_typing` |
| `limit` / `approved_set` | when kind requires them |

## Tests

```bash
python3 -m unittest tools.adr_pack.tests.test_adr_pack -v
```
