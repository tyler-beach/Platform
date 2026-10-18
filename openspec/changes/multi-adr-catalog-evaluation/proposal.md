## Why

TTL and PDB prove the shared spine, but a useful GitHub prototype needs many ADRs across technology domains so a generic tech spec or code package can surface multiple deviation/alignment outcomes—not two hardcoded checks.

## What Changes

- Add 100 synthetic, unadjudicated ADRs spanning security, identity, data, reliability, networking, API, cloud, observability, CI/CD, privacy, messaging, and related domains.
- Publish an approved typed-requirement catalog and expanded predicate registry bound to collectors by domain (not ADR ID).
- Add `numeric_min` and `dependency_forbidden` engine kinds where corpus families need them.
- Add a structured evidence-package collector and multi-requirement evaluator that returns per-requirement outcomes plus an aggregate summary (including mixed/partial coverage).
- Ship sample packages demonstrating multi-finding evaluation from tech-spec + code inputs.

## Capabilities

### New Capabilities
- `multi-adr-catalog-evaluation`: Catalog-driven multi-requirement evaluation of a pinned evidence package.

### Modified Capabilities
- `shared-evaluation-spine`: Expand kinds/predicates/collectors; evaluation must remain kind-based with no ADR-ID branching.

## Impact

- `.poc/requirement_catalog/` (ADRs, requirements.jsonl, predicates, samples, generator)
- `.poc/requirement_engine/` (registry load, engine kinds, package collector/evaluator)
- Docs clarifying synthetic/unadjudicated status and outcome aggregation
- Offline PoC only; no claim of production detector quality or independent adjudication
