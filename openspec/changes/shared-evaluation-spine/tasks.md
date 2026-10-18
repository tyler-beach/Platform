## 1. Shared spine core

- [x] 1.1 Add predicate registry and collector capability map
- [x] 1.2 Expand engine with `boolean_required` and `set_membership`
- [x] 1.3 Add requirement normalizer with approval/provenance validation
- [x] 1.4 Add config/JSON collector for registered numeric/bool/string predicates
- [x] 1.5 Route PDB collection through registry-bound Kubernetes capability

## 2. TTL collapse

- [x] 2.1 Replace TTL local compare with `engine.evaluate(numeric_max)`
- [x] 2.2 Preserve TTL result contract and deterministic fingerprints
- [x] 2.3 Add regression tests proving engine path and no ADR-ID branching

## 3. Product surfaces

- [x] 3.1 Update reusable evaluation docs for registry + normalization
- [x] 3.2 Update pathfinder-flow stages/nodes for Normalization
- [x] 3.3 Update home pipeline / demo copy for shared spine
- [x] 3.4 Update site experience tests

## 4. Verification

- [x] 4.1 Run focused Python unit tests for engine, registry, normalizer, TTL, PDB
- [x] 4.2 Run site experience / interactive tests
- [ ] 4.3 Open PR, confirm CI, merge to main
