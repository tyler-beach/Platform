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

Use the offline import tool (no model calls): [`tools/adr_pack/README.md`](../../tools/adr_pack/README.md).

1. Copy company ADR markdown into a directory (private clone recommended).
2. `python3 -m tools.adr_pack validate path/to/adrs`
3. `python3 -m tools.adr_pack scaffold path/to/adrs --predicates data/adr_catalog/predicates.json`
4. Optional local Claude drafts via Claude Code CLI (no API key; dry-run first): `python3 -m tools.adr_pack suggest path/to/adrs --predicates data/adr_catalog/predicates.json` then `--execute --yes` if you accept usage.
5. Humans complete/approve each `.md.req.json` sidecar (kind, predicate, subject, applicability).
6. `python3 -m tools.adr_pack build path/to/adrs --out path/to/pack --base-predicates data/adr_catalog/predicates.json`
7. Point Pathfinder catalog mode at that pack; run Go tests / a sample evaluate.
8. Keep `label_status` honest until requirements are reviewed.

The prototype generator remains available: `python3 data/adr_catalog/generate_pack.py`.

Do **not** paste private ADR bodies into public issues. For private org use, run Pathfinder in a private clone with the same pack layout.

## Sample package

`sample_packages/session-and-pdb/package.json` is a public/synthetic tech-spec + YAML fixture designed to extract multiple observations and produce mixed confident outcomes against the engineering-control portion of this pack. Many org-wide rows will stay `inconclusive` until observations exist—that is expected.
