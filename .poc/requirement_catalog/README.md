# Multi-ADR requirement catalog (synthetic)

This catalog contains **100** synthetic ADRs (`ADR-101`–`ADR-200`) with approved typed requirements for offline multi-requirement evaluation.

- **Not** independently adjudicated production policy.
- Collectors bind by **predicate**, not ADR ID.
- Evaluate with the Go CLI (`go/pathfinder/cmd/pathfinder-evaluate-package`). Python `.poc/requirement_engine/evaluate_package.py` remains an offline oracle.

## Domain coverage

- `api`: 8
- `cicd`: 8
- `cloud`: 7
- `compliance`: 5
- `data`: 6
- `frontend`: 5
- `identity`: 7
- `messaging`: 7
- `ml`: 7
- `networking`: 6
- `observability`: 7
- `platform`: 2
- `privacy`: 4
- `reliability`: 9
- `security`: 7
- `storage`: 2
- `supply-chain`: 3

## Files

- `adrs/` — synthetic ADR markdown
- `requirements.jsonl` — approved typed requirements
- `predicates.json` — registry seed loaded by the engine package
- `sample_packages/` — example tech-spec/code evidence packages
