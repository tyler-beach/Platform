## MODIFIED Requirements

### Requirement: Publish bounded synthetic and internal run records
The documentation build MUST generate the synthetic walkthrough in every site build. It MAY publish bounded Actions run/job/step metadata only when `PAGES_ACTIONS_HISTORY_ENABLED` is exactly `true`, the repository is organization-owned and has `private` or `internal` visibility, and the GitHub Pages API reports `public: false`. It MAY additionally publish CSV-backed run, finding, evidence, observation, confidence, and coverage records only when `PAGES_REAL_RUN_DATA_ENABLED` is exactly `true` and the same repository and Pages checks pass. Each opt-in MUST be evaluated independently. Pull-request builds MUST publish neither data class. Actions history MUST contain only allowlisted metadata and repository-bound run links; it MUST NOT fetch workflow artifacts. The ledger projection MUST contain only the existing allowlisted, provenance-validated, redacted fields. If Actions history is enabled while ledger export is disabled, the snapshot MUST contain Actions history and zero detailed ledger runs.

#### Scenario: Actions history is enabled without ledger export
- **GIVEN** an organization-owned internal repository has Pages `public: false`
- **AND** `PAGES_ACTIONS_HISTORY_ENABLED` is exactly `true`
- **AND** `PAGES_REAL_RUN_DATA_ENABLED` is absent or false
- **WHEN** the documentation workflow builds the site
- **THEN** it publishes bounded Actions run, job, and step metadata
- **AND** it publishes zero CSV-backed ledger records
- **AND** it does not clone the ledger branch

#### Scenario: Ledger export is enabled without Actions history
- **GIVEN** an organization-owned private repository has Pages `public: false`
- **AND** `PAGES_REAL_RUN_DATA_ENABLED` is exactly `true`
- **AND** `PAGES_ACTIONS_HISTORY_ENABLED` is absent or false
- **WHEN** the documentation workflow builds the site
- **THEN** it publishes the validated bounded ledger projection
- **AND** it does not call the GitHub Actions history API

#### Scenario: Either export is enabled on an ineligible repository
- **GIVEN** either export opt-in is exactly `true`
- **AND** the repository is user-owned or public, or Pages is public or unverifiable
- **WHEN** the documentation workflow evaluates the visibility gate
- **THEN** it fails before reading run history or cloning the ledger

#### Scenario: Pull-request build
- **GIVEN** a pull request changes documentation or demo code
- **WHEN** the Pages build runs
- **THEN** neither real Actions history nor CSV-backed ledger records are included
- **AND** the synthetic walkthrough remains available
