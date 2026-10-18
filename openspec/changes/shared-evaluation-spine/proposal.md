## Why

Deviation checks still fork into ADR-specific pipelines (session TTL) and only two engine kinds. That does not scale: new ADRs must become data on a shared spine (normalize → collect by domain → evaluate by kind), not new investigate modules.

## What Changes

- Introduce a predicate registry and collector capability map so collectors bind by evidence domain/predicate, not ADR ID.
- Collapse session TTL decisioning onto `engine.evaluate` while preserving the existing TTL result contract for replay tests.
- Add a requirement normalizer that validates typed requirement candidates and approval state without inventing evidence.
- Expand shared engine kinds with `boolean_required` and `set_membership` (corpus-backed families).
- Keep PDB collection as a Kubernetes domain collector bound through the registry; document that new ADRs reuse kinds/collectors.
- Update workflow/demo surfaces so visitors see Normalization as an explicit stage in the shared flow.

## Capabilities

### New Capabilities
- `shared-evaluation-spine`: Predicate registry, requirement normalization, kind-based shared evaluation, and domain collectors as the path for ADR checks.

### Modified Capabilities
- `interactive-investigation`: Workflow/demo must surface normalization and the shared kind-based evaluation path.

## Impact

- `.poc/requirement_engine/` (engine, registry, normalizer, collectors)
- `.poc/session_ttl/investigate.py` (uses shared engine for decisions)
- Site/workflow pages (`public/pathfinder-flow`, `src/site.jsx`, DemoExplorer/tests)
- Docs: `REUSABLE_REQUIREMENT_EVALUATION.md`
- Offline PoC only; no live cluster/cloud adapters
