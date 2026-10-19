# ADR pack import tool (deterministic, no model)

## Why

Company testers need to aim Pathfinder at their own ADRs. Today the real pack is generated from hand-authored typed rows. Free-form ADR markdown alone is not enough: Pathfinder evaluates typed requirements (kind, predicate, subject, limits, applicability). Sending every ADR through a model is undesirable for privacy and review. Operators need a local tool that validates ADR structure, scaffolds the missing typed fields, and builds a pack only from human-completed rows—without calling Claude or any network model API.

## What changes

- Add an offline Python CLI under `tools/adr_pack` with three commands:
  - `validate`: lint markdown ADR structure and report readiness gaps.
  - `scaffold`: write draft typed sidecars (`.md.req.json`) next to ADRs (never invent approved requirements).
  - `build`: emit `requirements.jsonl`, merged `predicates.json`, and `catalog_manifest.json` from completed sidecars + ADR digests.
- Optional deterministic heuristics may *suggest* kind/limit/predicate candidates and mark them `needs_review`; they MUST NOT auto-approve.
- Optional local Claude assist via `suggest` is opt-in, budgeted, cached, dry-run by default, and MUST NEVER auto-approve. Default `validate`/`scaffold`/`build` remain offline.

## Non-goals

- Semantic understanding of arbitrary ADR prose as trusted policy.
- Replacing architecture-owner review of typed requirements.
- Migrating Bedrock/pgvector stores in this change.
- Changing the Go evaluation engine contract.

## Acceptance criteria

- `validate` fails closed on missing Decision section / unreadable files and warns on missing domain/status.
- `scaffold` creates sidecars with `label_status=needs_human_typing` and does not overwrite completed approved sidecars by default.
- `build` refuses rows that are incomplete or still `needs_human_typing` / unapproved.
- Heuristic suggestions are labeled and never set `approval_state=approved`.
- Unit tests cover parse, validate, scaffold idempotence, and build gates.
- OpenSpec validates for this change.

## Risks and rollback

- Over-trusting heuristic suggestions — mitigated by explicit needs_review / no auto-approve.
- Rollback: delete `tools/adr_pack` and the OpenSpec change; existing `generate_pack.py` remains.
