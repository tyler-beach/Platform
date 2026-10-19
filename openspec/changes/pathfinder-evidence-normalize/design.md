# Design: Pathfinder evidence normalize

## Context

Today `pkgcollect.CollectObservations` validates schema-bound packages and returns map observations. The evaluation engine re-validates fields and detects value conflicts. Paste extraction emits `paste_span` locators with line/byte ranges. There is no shared normalize module aligning with `docs/contracts/EVIDENCE.md` locator precision or deterministic package ordering.

## Goals / non-goals

Goals: pure normalize core; precision; canonical sort; conflict classification; thin collect adapter.

Non-goals: full evidence protobuf, model calls, mutating paste drop rules, Pages UI.

## Decisions

1. **Package location:** `go/pathfinder/internal/evidence` owns pure normalize/sort/conflict helpers. `pkgcollect` remains the I/O + registry adapter for `pathfinder-evidence-package-v1`.
2. **Observation shape:** keep `map[string]any` for engine compatibility; normalize adds `locator_precision` and `normalizer_version`.
3. **Precision derivation:**
   - `EXACT` when locator has typed kind and a line-addressable or byte span (`line`/`start_line` with end ≥ start, or `start`/`end` byte range), or an `excerpt_sha256`.
   - `APPROXIMATE` when locator has a non-empty kind and a non-empty symbolic `value` (e.g. `yaml_resource`, `issue_claim`) without a span.
   - `UNAVAILABLE` when only a kind is present or precision cannot be established.
4. **Conflicts:** `ClassifyConflicts` groups by `(predicate, subject)` and reports groups whose values are not equal. Normalize does not drop authored rows.
5. **Sort key:** ascending `(predicate, subject, artifact_id, path, evidence_id)` so order is stable for fingerprints.
6. **Ownership:** returned observation maps are newly allocated; callers must not mutate after stage handoff.

## Alternatives considered

- Expand engine validation only — rejected; would keep normalize logic split from collect and harder to test in isolation.
- Fail collect on any conflict — rejected; would change existing evaluate outcomes for packages that rely on `conflicting_evidence`.
- Full EvidenceItem structs now — deferred; maps keep the PoC moving without a schema migration.

## Operational notes

- No network/model effects.
- Errors are domain validation errors (typed message), distinct from I/O.
- Telemetry: existing `package_build` stage remains the span name; no new OTEL attributes with evidence content.
