## MODIFIED Requirements

### Requirement: Publish bounded synthetic and internal run records
The documentation build MUST generate an in-page walkthrough from the checked-in fixture and mock provider. It MAY additionally publish bounded real run records only when the repository is organization-owned, repository visibility is `private` or `internal`, the GitHub Pages API reports `public: false`, and `PAGES_REAL_RUN_DATA_ENABLED` is exactly `true`. The real-data step MUST NOT run for pull-request events. Internal Pages run links and API requests MUST use the cloned repository identity. It MUST include only allowlisted summary, stage, evidence, observation/coverage, confidence, and finding fields. It MUST NOT publish credentials, prompts, provider request/response payloads, or raw workflow artifacts. Every evidence and observation reference MUST resolve by artifact ID to a unique artifact row in the same run, with matching path and full SHA-256; stored excerpt hashes MUST match their source text before redaction. Every non-inconclusive finding MUST resolve all cited evidence IDs in the projection, and the explorer MUST show all cited evidence before supplemental records. Same-origin static snapshots MUST use same-origin credentials when needed for privately published Pages, while cross-origin snapshot URLs are rejected. GitHub API requests MUST omit browser credentials and MUST NOT include an authorization token.

#### Scenario: Internal organization repository has private Pages
- **GIVEN** an organization-owned repository has visibility `internal`
- **AND** the Pages API reports `public: false`
- **AND** `PAGES_REAL_RUN_DATA_ENABLED` is exactly `true`
- **WHEN** the docs workflow prepares its Pages artifact
- **THEN** the bounded allowlisted run projection is enabled

#### Scenario: Personal repository or public Pages is configured
- **GIVEN** real-data mode is enabled for a user-owned repository, a public repository, or Pages that is public or unverifiable
- **WHEN** the docs workflow evaluates the visibility guard
- **THEN** the export is rejected before cloning the ledger
