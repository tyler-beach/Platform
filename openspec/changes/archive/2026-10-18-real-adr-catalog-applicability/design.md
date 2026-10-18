# Design: Real ADR catalog applicability

## Approach

1. **Catalog pack** on disk: `data/adr_catalog/` (or `.poc` transition) with `adrs/*.md`, `requirements.jsonl`, `catalog_manifest.json` (hash of pack).
2. **Applicability** pure function: `(package scope + artifact languages/paths, requirement row metadata) → in_scope bool`.
3. **Evaluate** only in-scope rows; out-of-scope → `not_applicable`. Empty in-scope set → aggregate `not_applicable_only` or explicit `no_applicable_adr` disposition in report metadata.
4. **Demo mode**: `PATHFINDER_CATALOG=synthetic` keeps ADR-101–200 for Pages/fixtures.

## Alternatives

- Embeddings first: deferred until metadata filters are honest.
- Single hard-coded ADR: too small for org use after PR intake.

## Risks

- Sparse packages look “clean” if applicability is too narrow — mitigate with explicit coverage counts in comments.
- Hand-authored requirement rows diverge from ADR prose — require hash link to ADR section + review checklist.
