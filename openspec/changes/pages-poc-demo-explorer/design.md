# Design: constrained static site plus internal run projection

## Information sources

The browser has no credential. It asks GitHub's REST API for a fixed allowlist of workflows, validates response shape/IDs/URLs, and renders all API values as text. For selected runs it requests only job/step status. Rate limits, network failure, and malformed responses render an explicit status with links to Actions.

Every docs build generates a fixture walkthrough by running the Go fixture with the offline mock provider. A Python exporter maps CSV/JSON outputs through an allowlist into `adr-demo-run-v1`; it rejects any artifact path outside `.poc/fixtures/go` and labels the sample synthetic.

The docs workflow may add `adr-demo-history-v1` from `poc-database` only when all gates pass:

1. Repository visibility is exactly `private`.
2. The authenticated Pages API response has `public: false` (private/internal audience).
3. Repository variable `PAGES_REAL_RUN_DATA_ENABLED` equals the exact string `true`.

If the variable is false or absent, real data is not cloned. If the variable is true but either visibility check cannot be verified, the build fails before exporting the ledger. The exporter selects a bounded set of recent runs and an explicit subset of CSV columns; it omits model transactions, prompts, raw provider responses, and source artifacts. It redacts quoted literals and credential-shaped patterns from displayed evidence, retains full artifact SHA-256 and locator, reports a redaction flag, and hashes the displayed excerpt separately.

The real-data step is excluded from pull-request events so untrusted proposed code cannot execute with the repository token or read the private ledger. The API history snapshot includes the checked-out repository identity; the site validates and uses that identity for run links and browser API requests, so the internal clone does not link back to the public source repository.

## Interaction

- A stage rail offers previous/next/play/pause; playback is user initiated and follows sample events.
- Selecting a stage updates its explanation and count summary.
- Run history shows workflow name, run number, status/conclusion, event, branch, commit prefix, and time. Expanding reveals jobs and steps. If a selected run ID matches internal snapshot data, it also reveals real stages, finding, evidence, observations, confidence components, and collection coverage.
- Original Actions run link remains available to inspect artifacts on GitHub.
- Status uses text as well as color; animations honor `prefers-reduced-motion`.

## Refresh path

The existing docs workflow runs on source changes and manual dispatch. It also runs after `ADR Deviation PoC Analysis` or `ADR Deviation Labeled Evaluation` completes, checks out the default branch, clones the latest database branch after analysis has written it, generates the site, and deploys through the existing Pages artifact flow. Workflow-run refreshes are accepted only for trusted default-branch runs, excluding pull requests. Real-data export is limited to the default-branch and eligible workflow-completion builds that can deploy; pull requests and non-default manual builds remain fixture-only.

## Failure and security

The fixture build makes no model call. The Pages build token has contents-read and Pages-read only; it is never placed in the artifact. API responses/source/ADR text are untrusted; never interpolate them into HTML. The explorer never invokes workflow dispatch. Public repository builds never include the real database. Private repository visibility alone is insufficient; the Pages `public` flag and explicit opt-in are required.

## Test mapping

- Snapshot projection/privacy/redaction: Python tests over generated fixture and mutated canary evidence.
- REST response validation, safe URLs, bounds, attempt-specific job requests, API failure: Node built-in tests with mock responses, no network.
- Page workflow links, stage controls, score caveat, accessibility, and workflow gates: Python docs contract tests plus strict MkDocs build.
- End-to-end: run Go fixture with mock, export snapshot, build MkDocs, validate all static JSON and links.
