# GitHub PoC OpenTelemetry and usage dashboard

## Why

The current GitHub PoC has a lean Pathfinder job ledger and Pages run/evaluation views, but it lacks analysis-level traces and an aggregate product dashboard. The repository has OTel design guidance, but the Go Pathfinder CLI does not yet initialize or export OTel telemetry. Pages currently gets run-ledger projections during site builds, so updates can trigger a full site deployment.

## What changes

- Instrument the Go Pathfinder issue-analysis and package-evaluation commands with OpenTelemetry traces and low-cardinality metrics.
- Export OTLP/HTTP only when an administrator configures an endpoint; bound export time and never make analysis success depend on telemetry delivery.
- Extend the lean Pathfinder job record with validated outcome counts and generate a bounded aggregate JSON projection on the existing `pathfinder-jobs` branch.
- Persist fixed-key stage run/error/skipped counts and measured durations from the same OTel instrumentation points, then expose their 90-day aggregates in the dashboard without storing raw traces.
- Add a Pages Usage dashboard that fetches a same-origin projection embedded in the Pages artifact. Full site builds persist a deployable static bundle; completed Pathfinder analyses replace only its summary JSON and redeploy the saved bundle without rerunning the site build/tests.
- Clearly report AI usage/spend as unavailable/not metered in this PoC because the Pathfinder workflow does not make model calls. Do not manufacture zero cost or token data.

## Non-goals

- No LLM/model call integration or AI spend ledger implementation in this change.
- No user-held credentials, external dashboard service, or new database. Aggregate data is published only to a verified private GitHub Pages site.
- No OTel vendor selection; backend endpoint/headers are optional repository configuration.
- No traces containing issue bodies, source code, evidence excerpts, secrets, or full prompts.

## Acceptance criteria

- OTel spans and metrics cover issue intake, package creation, catalog/evaluation, report generation, comment publication, and terminal result; telemetry attributes are allowlisted and low-cardinality.
- OTLP export is disabled without an endpoint, has a bounded deadline when configured, and failure is surfaced safely without changing the analysis outcome.
- Job record tests prove outcome counts are allowlisted/non-negative and source/report bodies are not added.
- Telemetry and dashboard tests prove stage measurements are real runtime observations, allowlisted, aggregated deterministically, and contain no source/run/trace identifiers.
- Dashboard projection tests prove aggregation is deterministic, bounded, schema-versioned, excludes per-issue identifiers/content, and handles old/malformed records safely.
- The Pages dashboard loads the projection from its same-origin artifact and presents stale/unavailable states, current PoC limitations, and no AI metering as unavailable.
- Completed Pathfinder analysis runs trigger a Pages deployment after the serialized ledger workflow completes, reusing a persisted site bundle so npm/Vite/docs generation and site tests do not rerun; deployments are serialized.
- The Pages build embeds real aggregate data only when repository metadata says the repository is private and Pages metadata says the site is private. Every other case embeds a valid empty projection.
- React data/view tests and Go tests pass; Pages build and workflow validation pass.

## Risks and rollback

- The aggregate is sensitive operational data. The Pages build must fail closed and embed an empty projection unless both the repository and Pages visibility are verified private. The existing job ledger remains separate and contains identifiers.
- Pages updates still redeploy the complete static bundle after each analysis, but skip the full site build, tests, and fixture generation.
- OTLP endpoints and headers are administrator-controlled; never echo them into logs or Pages. Missing endpoint means no export.
- Rollback removes the Usage route and projection writer/exporter configuration while leaving analysis and the existing ledger operational.

## Owner decisions captured

- Reuse a persisted site bundle and redeploy it after completed analysis runs; this lets private Pages enforce access without browser-held credentials while avoiding a full site rebuild each time.
- Keep the five-minute same-origin refresh cadence for pages already open in a browser.
- GitHub Actions repository variable `OTEL_EXPORTER_OTLP_ENDPOINT` and secret `OTEL_EXPORTER_OTLP_HEADERS` are optional configuration, not committed values.
