# Design: GitHub PoC OTel and dashboard

## Scope and choices

### Telemetry

The Pathfinder CLI is a short-lived Go process in GitHub Actions. Add a small `internal/telemetry` bootstrap that configures OpenTelemetry trace and metric providers with OTLP/HTTP exporters from standard environment variables. With no endpoint, use the SDK no-op providers. Use bounded batch/periodic export and a short shutdown flush deadline. Export failure is diagnostic only and must not replace the analysis exit status.

Instrument the issue CLI with a root run span and nested bounded stage spans: intake, catalog load, package normalization, evaluation, report persistence, comment publication, and job record creation. Instrument package-evaluation similarly. Add counters/histograms with only bounded dimensions such as command, stage, outcome, error class, comparison mode, and catalog mode. Do not use issue number, job/run IDs, repository, source paths, content, or evidence IDs as metric labels. Spans may carry opaque run/job identifiers only when provided, but no issue body/source text.

The current analysis runtime is deterministic and does not call a model. Do not emit GenAI spans or fabricated token/cost metrics. AI usage is displayed as `not_metered`/not available until a model adapter exists and records provider-reported usage in a durable ledger.

### Private Pages dashboard refresh

The serialized `pathfinder-jobs` ledger write continues to compute `dashboard/summary.json` with each append. A full Pages build persists the ready-to-deploy static site bundle on the private `pathfinder-pages` branch, including a safe empty summary fallback. After a Pathfinder analysis completes, a lightweight workflow verifies the source-run artifact, checks repository and Pages visibility with authenticated GitHub API calls, checks out the saved bundle, and replaces only `data/summary.json`. It then uploads and deploys that saved bundle without running npm install, Vite, documentation generation, tests, or demo fixture generation. Only when the repository is an organization-owned private repository and Pages metadata reports `public: false` does it copy the bounded aggregate summary into the saved bundle; otherwise the empty summary is retained. The dashboard reads a fixed same-origin URL and polls every five minutes. Pages deployments share a serialized concurrency group.

The aggregate is built with a Go package/command for deterministic, testable transformation. The same in-process stage measurements recorded by the OTel instruments are snapshotted into the lean per-run job record: fixed stage/outcome keys, run counts, total duration, and maximum duration. The serialized writer aggregates these bounded measurements into daily and window totals. This gives the Pages dashboard actual runtime telemetry without a persistent OTLP receiver or raw trace storage. Optional OTLP export remains available independently.

The projection accepts supported ledger schema versions, ignores invalid lines without exposing them, sorts date buckets, bounds the history window and output size, and only outputs aggregate analysis/outcome and operational stage metrics. It never emits issue number, run URL/ID, package ID, source/report hash, repo identifier, body, trace/span identifiers, or finding content. GitHub Pages reads the compact JSON projection; it does not query raw per-run telemetry.

No credential is sent to the browser. The Actions token reads the private aggregate during publication only. Visibility lookup failure is fail-closed: the saved site bundle retains the empty projection. Every analysis-triggered refresh redeploys the static site bundle, but does not rebuild the site; updates are visible after deployment completes.

### Data semantics

Add outcome counts to the lean per-run Pathfinder ledger record from the already validated report counts. Keep all existing fields and branch path. Support legacy records without counts. Aggregate job execution status separately from domain outcomes; failed runs without a report do not increment an outcome count. Include jobs, successful/failed records and per-outcome counts, plus daily buckets. Include explicit schema version, window, record count, generation timestamp, and `model_metering: not_metered`.

The dashboard labels outcome distributions as PoC observations, not compliance or accuracy scores. Rates always disclose numerator/denominator and omit a rate when denominator is zero. It does not identify engineers, repositories, or individual issues.

## Security and failure behavior

- OTel endpoint/headers are supplied only through Actions configuration; no credentials are committed, printed, put in spans, or included in step summaries.
- OTLP requests have a strict timeout; analysis continues if telemetry export fails and the exporter reports a safe diagnostic.
- The dashboard fetches only a fixed same-origin data URL. No arbitrary URL or cross-origin URL may be loaded from snapshot content.
- Build-time publication verifies private repository and Pages access before copying any data branch projection. All failure paths preserve an empty summary and never fall back to a public/raw URL.
- Treat snapshot JSON as untrusted. Validate schema, timestamp, counts, date keys, and outcome names before rendering; render plain text only.
- Polling is single-flight, cache-busted, capped at five-minute cadence, and canceled on unmount. Manual refresh is available.
- The serialized ledger writer updates JSONL and projection in the same branch commit with bounded push retries. If projection generation fails, ledger behavior stays explicit and the writer reports failure rather than publishing a stale snapshot as fresh.

## Alternatives considered

- **Rebuild all Pages on each analysis:** rejected because it repeats docs/tests/Vite work unnecessarily. The chosen flow reuses the last generated bundle and redeploys it with the updated JSON.
- **Fetch GitHub Actions artifacts/API directly from browser:** artifacts require authorization and API rate limits/permissions; they expose much more data than the summary needs. Rejected.
- **Hosted dashboard/database:** outside the GitHub-only PoC scope and requires service credentials/operations. Deferred.
- **Persist raw OTel traces:** adds high-cardinality identifiers and sensitive-data risk to the Git-backed data branch without a trace query engine. Rejected; persist only bounded metric aggregates sourced from the same measured OTel stage events.

## Migration and rollback

No database migration. Ledger schema adds optional outcome-count fields compatibly; projection reader accepts older ledger records. Existing branch data remains. Rollback disables the new projection commit and Pages route; existing analysis and ledger records remain intact.
