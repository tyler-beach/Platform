# Proposal: Separate Pages workflow history from ledger publication

## Why

The Pages workflow currently uses one `PAGES_REAL_RUN_DATA_ENABLED` switch for both Actions run/job/step metadata and the much richer CSV-backed finding/evidence projection. A repository reader who wants a useful prior-run timeline must also opt into publishing detailed ledger records, even though the two data classes have different sensitivity and review requirements.

## What changes

- Add an exact `PAGES_ACTIONS_HISTORY_ENABLED=true` opt-in for bounded GitHub Actions run/job/step metadata.
- Keep `PAGES_REAL_RUN_DATA_ENABLED=true` as the separate opt-in for CSV-backed PoC run, finding, evidence, observation, confidence, and coverage rows.
- Require the same organization ownership, private/internal repository visibility, and Pages API `public: false` checks before either opt-in can publish data.
- Permit Actions history without ledger records; the exporter must produce a valid empty ledger projection plus the bounded Actions history in that mode.

## Scope and non-goals

This changes only Pages data selection. It does not make either export public, fetch workflow artifacts, change analysis behavior, or alter browser authentication. The synthetic walkthrough remains available in all builds.

## Acceptance criteria

- Actions history and ledger data can be independently enabled.
- Either enabled export fails closed unless the repository is organization-owned, private or internal, and Pages reports `public: false`.
- With Actions history enabled and ledger data disabled, the Pages snapshot contains workflow metadata and zero ledger run records.
- With ledger data enabled and Actions history disabled, no Actions API history request is made.
- The opt-in values must match exact lowercase `true`; PR builds never export either data class.

## Risks and rollback

Two variables add setup complexity. The runbook will state clearly which data each variable enables. Rollback removes the Actions-history flag and restores the shared switch behavior. Existing private Pages deployments must set the new Actions-history variable to retain their timeline.

## Decisions needing review

- This PoC uses separate flags because execution metadata and finding/evidence records have different exposure levels. Confirm the long-term configuration model before a production rollout; no enterprise policy decision is implied here.
