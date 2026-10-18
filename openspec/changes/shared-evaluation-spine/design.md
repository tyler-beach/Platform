## Context

The reusable evaluation doc already separates applicability, normalization, collection, shared evaluation, and results. PDB uses the engine; TTL does not. UI stages skip normalization.

## Goals / Non-Goals

**Goals**
- One decision path: typed requirement + observations → `engine.evaluate`
- Collectors register predicates; ADRs do not own collectors
- Normalizer fails closed on unsupported/ambiguous structure
- Demo/workflow shows: Decision → Scope → Normalize → Evidence → Assess → Review → Disposition

**Non-Goals**
- Parsing arbitrary ADR prose with production AI quality claims
- Live Kubernetes/cloud collectors
- Automatic ADR mutation from findings
- Unifying the async call-graph `model.assess` path in this change

## Decisions

1. **Kinds grow from families, not ADR IDs** — add `boolean_required` and `set_membership` alongside existing kinds.
2. **TTL adapter** — keep case validation and TTL result schema; replace local compare with engine observations + `numeric_max`.
3. **Registry is data** — predicates declare value type and collector id; unknown predicate → cannot collect / stay unnormalized.
4. **UI honesty** — normalization stage explains AI may propose structure, humans approve, evaluate stays deterministic.

## Risks / Trade-offs

- TTL result envelope differs from engine result → adapter mapping must preserve fingerprint invariants.
- Corpus `classify()` remains a label oracle; do not treat it as the runtime engine.
- Site stage renumbering may break string-match tests → update tests with the change.

## Migration

1. Registry + engine kinds + normalizer + tests
2. TTL → engine
3. PDB adapter uses registry lookup
4. Docs + workflow UI
5. CI on PR head before merge
