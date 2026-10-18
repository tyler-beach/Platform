# Real ADR catalog pack (prototype v1)

Working **prototype corpus** of 20 platform-style ADRs / 22 typed requirements under `adrs/`.

- **Default Pathfinder mode:** `real` (this pack)
- **Synthetic demo pack:** `.poc/requirement_catalog` via `PATHFINDER_CATALOG=synthetic` or `--catalog-mode=synthetic`
- **Labels:** `prototype_corpus_unadjudicated` — not independently adjudicated org policy
- **Regenerate:** `python3 data/adr_catalog/generate_pack.py`

## Domains

`api`, `cicd`, `identity`, `messaging`, `observability`, `reliability`, `security`

## Replace with your real ADRs

1. Add or replace markdown under `data/adr_catalog/adrs/` (or extend `generate_pack.py`).
2. Ensure every predicate exists in `.poc/requirement_catalog/predicates.json` (or extend that registry first).
3. Run `python3 data/adr_catalog/generate_pack.py` (or hand-edit `requirements.jsonl` + refresh `catalog_manifest.json`).
4. Run `go test ./...` in `go/pathfinder` and a local evaluate of `sample_packages/session-and-pdb`.
5. Keep `label_status` honest until requirements are reviewed (`prototype_corpus_unadjudicated` → your org’s status).

Do **not** paste private ADR bodies into public issues. For private org use, run Pathfinder in a private clone with the same pack layout.

## Sample package

`sample_packages/session-and-pdb/package.json` is a public/synthetic tech-spec + YAML fixture designed to extract multiple observations and produce mixed confident outcomes against this pack.
