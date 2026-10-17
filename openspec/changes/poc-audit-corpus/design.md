# Design: GitHub Actions audit workflow and ADR evaluation corpus

## Workflow boundary

Keep the current GitHub Actions workflow as the single manual analysis entry point. Add a `none` language option and an optional configuration root. The runner validates that a language is supplied whenever code files are selected, and skips compiler/parser toolchains when configuration-only mode is selected. Existing language-based runs continue to use the same entry point and inputs.

## Audit persistence

Do not widen or reorder existing CSV table headers because the `poc-database` branch may contain older snapshots and `CsvStore` enforces exact header equality. Add new append-only `observations.csv` and `collection_reports.csv` tables. Observation rows link to `run_id`, `observation_id`, optional evidence ID, schema version, artifact ID/version/hash, source locator, collector/version, normalized predicate/subject/value, resolution, evidence class and redaction marker. Coverage rows link to run/source type/collector and record completeness, inspected/emitted counts, unsupported/failed paths and bounded diagnostics.

Diagnostics must be safe for persistence: error categories and source locations are retained, but parser exception text that can echo source bytes is not. Source excerpts and code call expressions redact quoted string literals and recognized credential patterns before they enter model context, run artifacts or CSV evidence; full artifact hashes and exact locators remain pinned. The structured event stream records stage start, completion status and bounded counts. JSON run artifacts remain the detailed portable package; the CSV tables provide queryable, linked audit summaries.

## Corpus shape

Store each ADR as ordinary natural-language Markdown. Keep test labels and exact evidence expectations in a separate JSONL manifest so no machine-only syntax is required in the ADR itself. Each case points to one immutable YAML/JSON fixture artifact and an exact locator/value expectation, and records whether the expected assessment is deviation, no-deviation, or inconclusive. The 50 cases cover availability/disruption budgets, authentication, authorization, encryption/key management, network controls, secrets, data handling, resilience, logging/monitoring, deployment/runtime, and API behavior.

The offline audit validates manifest and artifact hashes, extracts the stated requirement passage, invokes the existing generic configuration collector, and checks whether the expected fact and locator are present or correctly absent. Cases requiring runtime or unsupported source capabilities must be inconclusive. Mock assessment abstention is a separate reported signal and is not scored as live semantic accuracy.

## Verification

- CLI behavior test: config-only selection works without `--language`; code selection without a language is rejected.
- CSV tests: observation and coverage records round-trip; old existing headers are unchanged; fresh/legacy database initialization creates additive tables.
- Privacy tests: canary credential values never appear in observations, CSV rows, prompts, captured output, or diagnostics.
- Corpus tests: 50 unique ADRs, valid manifest/schema, valid hashes and locators, and complete domain coverage.
- Workflow checks: YAML syntax/contract assertions plus local invocation of the exact configuration-only CLI path.
- Evaluation report: corpus extraction and evidence mapping metrics are distinct from semantic outcome quality and confidence-score calibration.
