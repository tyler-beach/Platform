## ADDED Requirements

### Requirement: Demonstrate the runnable PoC accurately
The documentation site MUST explain how to launch the manual analysis and evaluation workflows, how to inspect outputs, and distinguish implemented PoC behavior from proposed production architecture. It MUST label mock-generated data and describe the evidence-strength score as distinct from calibrated probability.

#### Scenario: Visitor follows a PoC run
- GIVEN the visitor opens the demo page
- WHEN the visitor follows the launch instructions
- THEN the page links to the manual PoC analysis and evaluation workflows
- AND explains the stages, inputs, outputs, and run artifact location
- AND makes clear that mock mode performs no model call

#### Scenario: Visitor interprets confidence
- GIVEN the page displays a confidence score
- WHEN the visitor reads its explanation
- THEN it is described as an evidence-support score with dimensions and guardrails
- AND it is not represented as a probability or calibrated model confidence

### Requirement: Publish bounded synthetic and internal run records
The documentation build MUST generate an in-page walkthrough from the checked-in fixture and mock provider. It MAY additionally publish bounded real run records only when repository visibility is `private`, the GitHub Pages API reports `public: false`, and `PAGES_REAL_RUN_DATA_ENABLED` is exactly `true`. The real-data step MUST NOT run for pull-request events. Internal Pages run links and API requests MUST use the cloned repository identity. It MUST include only allowlisted summary, stage, evidence, observation/coverage, confidence, and finding fields. It MUST NOT publish credentials, prompts, provider request/response payloads, or raw workflow artifacts.

#### Scenario: Documentation build exports fixture output
- GIVEN the checked-in synthetic Go fixture and mock provider
- WHEN the docs workflow builds the site
- THEN a versioned fixture walkthrough is generated from actual PoC run output
- AND the output is labeled synthetic and mock-generated
- AND detailed stages can be explored without model credentials

#### Scenario: Fixture exporter sees a non-fixture source path
- GIVEN a fixture run bundle includes an artifact outside the approved fixture root
- WHEN the Pages snapshot exporter runs
- THEN export fails closed without copying that artifact content into Pages data

#### Scenario: Internal site exports real run data
- GIVEN the repository is private
- AND the Pages API confirms `public: false`
- AND the repository variable `PAGES_REAL_RUN_DATA_ENABLED` is exactly `true`
- WHEN the docs workflow projects the `poc-database` ledger
- THEN it emits a bounded, allowlisted set of run summaries, stages, findings, evidence, observations, confidence, and coverage
- AND redacts quoted literals and credential-shaped evidence text
- AND preserves original artifact hashes and source locators
- AND marks redacted excerpts and records displayed-excerpt hashes
- AND excludes prompts, credentials, provider payloads, and raw artifacts

#### Scenario: Real-data gate is not verified
- GIVEN real-data mode is explicitly enabled but the repository is public, Pages is public, or the Pages API cannot confirm private access
- WHEN the docs build evaluates the gate
- THEN it fails with an explicit error before cloning or exporting the ledger
- AND no real run data is copied into the Pages artifact

#### Scenario: Real-data mode is not enabled
- GIVEN the repository variable is absent or not exactly `true`
- WHEN the docs workflow builds the site
- THEN it does not clone the `poc-database` branch
- AND the synthetic fixture walkthrough remains available

#### Scenario: Analysis or evaluation workflow completes
- GIVEN the `ADR Deviation PoC Analysis` workflow writes the CSV ledger or the `ADR Deviation Labeled Evaluation` workflow completes
- AND the triggering workflow run is on the default branch and did not originate from a pull request
- WHEN either workflow completes
- THEN the docs workflow rebuilds from the default branch and latest ledger branch
- AND the selected run becomes explorable after Pages deployment

#### Scenario: Pull-request evaluation completes
- GIVEN the labeled evaluation workflow completes for a pull request
- WHEN the workflow-run event reaches the docs workflow
- THEN the privileged Pages build is skipped
- AND no private ledger is projected or deployed

### Requirement: Browse workflow history safely
The static site MUST allow a visitor to browse recent runs for configured PoC workflows and inspect job/step statuses. It MUST use no browser secret, MUST NOT trigger or mutate a workflow, MUST render untrusted API data as text, and MUST provide a useful fallback when the API is unavailable or rate-limited.

#### Scenario: Recent run history is available
- GIVEN GitHub's Actions API is reachable
- WHEN the demo page loads
- THEN recent runs for allowlisted workflows are listed
- AND selecting a run shows jobs and steps with status and timestamps
- AND a matching internal record is shown when present
- AND links open the original workflow run

#### Scenario: Actions API unavailable or rate-limited
- GIVEN the API request fails, is rate-limited, or returns malformed data
- WHEN the page requests run history
- THEN the static fixture walkthrough remains usable
- AND the visitor sees an explicit status and link to Actions

#### Scenario: Malicious API strings are returned
- GIVEN a branch name, workflow title, or step title contains HTML-like content
- WHEN it is shown in the page
- THEN it is rendered as text and cannot execute markup or script

### Requirement: Accessible workflow animation
The demo MUST provide controllable stage navigation and playback. It MUST not autoplay, MUST expose stage state to assistive technology, and MUST honor the user's reduced-motion preference.

#### Scenario: Visitor plays and navigates stages
- GIVEN the visitor chooses the walkthrough
- WHEN they use previous, next, play, or pause controls
- THEN the active stage and corresponding sample output update in order
- AND the active stage is announced accessibly

#### Scenario: Reduced motion is requested
- GIVEN the operating system requests reduced motion
- WHEN the site animates stage progress
- THEN movement is removed or reduced while stage controls and status remain usable
