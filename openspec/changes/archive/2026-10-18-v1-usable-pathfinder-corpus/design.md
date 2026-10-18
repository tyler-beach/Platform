# Design: Usable V1 Pathfinder corpus + defaults

## Approach

1. **Generator-owned pack** under `data/adr_catalog/` (`generate_pack.py`) produces ADR markdown, `requirements.jsonl`, slim `predicates.json`, and `catalog_manifest.json`. Hand-edited `docs/adr/*` remain the narrative sources for SESSION-TTL/PDB; generator embeds copies.
2. **Default mode = real.** Empty `PATHFINDER_CATALOG` / `--catalog-mode` resolves to `real`. Synthetic requires explicit `synthetic`.
3. **Issue form** adds Catalog pack choice (Real prototype default / Synthetic demo) and richer domain help listing pack domains.
4. **Comment UX** adds coverage: catalog identity, in-scope count, extracted observation count, short glossary for `inconclusive` / empty domains.
5. **Extractor** bumps version; add any missing high-confidence patterns for corpus predicates already in the allowlist.
6. **Model extract stub**: `PATHFINDER_ENABLE_MODEL_EXTRACT=1` reserved; without credentials the path no-ops / errors closed and never invents observations in CI default.
7. **Sample package + docs** for unaided first run and ops (14-day artifacts, `pathfinder-jobs`, re-run).

## Risks

- Prototype ADRs look “official” — mitigate with `prototype_corpus_unadjudicated` labels and README swap instructions.
- Defaulting to real changes report fingerprints / CI expectations — update tests and dry-runs explicitly.
