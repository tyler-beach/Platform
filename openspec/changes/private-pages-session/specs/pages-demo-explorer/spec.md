## MODIFIED Requirements

### Requirement: Publish bounded synthetic and internal run records
The documentation build MUST generate an in-page walkthrough from the checked-in fixture and mock provider. It MAY additionally publish bounded real run records only when repository visibility is `private`, the GitHub Pages API reports `public: false`, and `PAGES_REAL_RUN_DATA_ENABLED` is exactly `true`. The real-data step MUST NOT run for pull-request events. Internal Pages run links and API requests MUST use the cloned repository identity. It MUST include only allowlisted summary, stage, evidence, observation/coverage, confidence, and finding fields. It MUST NOT publish credentials, prompts, provider request/response payloads, or raw workflow artifacts. Same-origin static snapshot requests MUST use same-origin browser credentials when needed to read a privately published Pages site. Snapshot requests MUST reject cross-origin URLs. Requests to GitHub's API MUST omit browser credentials and MUST NOT include an authorization token.

#### Scenario: Authorized reader loads private Pages snapshots
- **GIVEN** a repository reader opens a privately published Pages site
- **WHEN** the explorer requests the synthetic walkthrough and internal run-history JSON from the site's own origin
- **THEN** the requests use same-origin credentials and load the snapshots
- **AND** no GitHub API credential is sent with those requests

#### Scenario: Snapshot URL points to another origin
- **GIVEN** a snapshot URL resolves to a different origin from the current Pages site
- **WHEN** the explorer prepares the request
- **THEN** it rejects the URL before making a network request

#### Scenario: Explorer requests GitHub Actions API data
- **GIVEN** the explorer needs public API fallback history
- **WHEN** it requests GitHub Actions API endpoints
- **THEN** it omits browser credentials and sends no Authorization header
