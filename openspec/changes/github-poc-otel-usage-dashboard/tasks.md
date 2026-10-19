## 1. OpenSpec and contract

- [x] 1.1 Review proposal, telemetry and dashboard scenarios, privacy boundary, and rollback.
- [x] 1.2 Add versioned dashboard projection schema and compatibility rules.

## 2. Go tests and implementation

- [x] 2.1 Add and run tests for ledger outcome-count extraction, allowlisting, and non-negative validation.
- [x] 2.2 Add and run tests for deterministic dashboard aggregation, legacy/malformed lines, time-window bounds, and absence of identifying/content fields.
- [x] 2.3 Add and run tests for optional OTel initialization, bounded export failure, fixed span names, and absence of span attributes.
- [x] 2.4 Implement ledger counts and pure dashboard aggregation/export command.
- [x] 2.5 Implement optional OTLP/HTTP tracing and metrics with bounded shutdown, redaction, and operation-level spans.

## 3. GitHub Actions data refresh

- [x] 3.1 Add optional endpoint/header configuration to the reusable analyze workflow without exposing secrets to job summaries or artifacts.
- [x] 3.2 Extend the serialized ledger job to regenerate `dashboard/summary.json` and commit ledger + aggregate together with bounded retries.
- [ ] 3.3 Verify branch-write failure remains visible and does not erase analysis comments/artifacts.
- [x] 3.4 Persist privacy-filtered stage measurements alongside each job record and aggregate them in the existing serialized writer.

## 4. Pages dashboard

- [x] 4.1 Add pure client-side schema/aggregate helpers and tests for invalid, stale, missing, and valid projections.
- [x] 4.2 Add Usage route with count/rate denominators, trends, refresh state, timestamp, and explicit not-metered AI state.
- [x] 4.3 Use a fixed same-origin data URL, safe rendering, and polling no more often than every five minutes.
- [x] 4.4 Document build-time summary publication and the analysis-triggered Pages deployment behavior.
- [x] 4.5 Display actual aggregated stage run/error counts and measured duration statistics with clear units and missing-data handling.
- [x] 4.6 Verify private repository and Pages visibility before embedding the aggregate; otherwise publish a valid empty summary.
- [x] 4.7 Trigger serialized Pages deployments after completed Pathfinder workflows and fetch the summary with the Actions token at build time.
- [x] 4.8 Persist the built site bundle for fast refresh and deploy the saved bundle after analysis without rerunning the full site build.

## 5. Verification

- [x] 5.1 Run Go unit tests and new projection/telemetry tests; record RED then GREEN evidence for the dashboard projection and browser validator.
- [x] 5.2 Run npm tests and production build.
- [x] 5.3 Validate OpenSpec and workflow YAML/permissions; inspect generated dashboard output for privacy fields.
- [x] 5.4 Review changed implementation files for credentials, source/prompt leakage, and repository-specific hardcoding.
- [x] 5.5 Verify telemetry-to-ledger-to-dashboard aggregation with privacy and compatibility regression tests.
