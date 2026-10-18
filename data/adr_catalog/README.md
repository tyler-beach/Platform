# Real ADR catalog pack (prototype v1.1)

Working **prototype corpus** of **200** organization-style ADRs / 200 typed requirements under `adrs/`.

| Block | Count | Source |
|---|---:|---|
| Engineering controls | 100 | Typed rows from `.poc/requirement_catalog` (API, identity, k8s, security, …) |
| Org-wide enterprise standards | 100 | Change/CAB, IAM/JML, FinOps, vendor, privacy/DPIA, BC/DR, architecture governance, … |

- **Default Pathfinder mode:** `real` (this pack)
- **Synthetic demo pack:** `.poc/requirement_catalog` via `PATHFINDER_CATALOG=synthetic` or `--catalog-mode=synthetic`
- **Labels:** `prototype_corpus_unadjudicated` — not independently adjudicated org policy
- **Regenerate:** `python3 data/adr_catalog/generate_pack.py`

## Domains (17)

`api`, `cicd`, `cloud`, `compliance`, `data`, `frontend`, `identity`, `messaging`, `ml`, `networking`, `observability`, `platform`, `privacy`, `reliability`, `security`, `storage`, `supply-chain`

## Replace with your real ADRs

1. Add or replace markdown under `data/adr_catalog/adrs/` (or extend `generate_pack.py`).
2. Ensure every predicate exists in this pack’s `predicates.json` (generator merges synthetic registry + org-wide predicates).
3. Run `python3 data/adr_catalog/generate_pack.py`.
4. Run `go test ./...` in `go/pathfinder` and evaluate `sample_packages/session-and-pdb`.
5. Keep `label_status` honest until requirements are reviewed.

Do **not** paste private ADR bodies into public issues. For private org use, run Pathfinder in a private clone with the same pack layout.

## Sample package

`sample_packages/session-and-pdb/package.json` is a public/synthetic tech-spec + YAML fixture designed to extract multiple observations and produce mixed confident outcomes against the engineering-control portion of this pack. Many org-wide rows will stay `inconclusive` until observations exist—that is expected.
