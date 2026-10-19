# pathfinder-otel Specification

## Purpose
Define safe optional OpenTelemetry instrumentation for the GitHub Actions Go Pathfinder PoC.

## ADDED Requirements
### Requirement: Export bounded Pathfinder telemetry over optional OTLP

Pathfinder analysis commands MUST emit traces and low-cardinality operational metrics through OpenTelemetry. OTLP/HTTP export MUST be opt-in through runtime configuration, bounded by a deadline, and non-blocking to the analysis result. Instrumentation MUST NOT record source content, issue body, prompts, evidence excerpts, secrets, or unbounded identifiers as metric attributes.

#### Scenario: Endpoint not configured
- **GIVEN** the Pathfinder CLI runs without an OTLP endpoint
- **WHEN** an analysis completes
- **THEN** the command uses no-op telemetry providers
- **AND** analysis output and exit status are unchanged

#### Scenario: Endpoint configured
- **GIVEN** a valid OTLP/HTTP endpoint is configured
- **WHEN** the Pathfinder CLI performs intake, normalization, evaluation, report persistence, or publication
- **THEN** it emits a correlated root span and bounded stage spans plus low-cardinality stage/result metrics
- **AND** it flushes telemetry within a configured short shutdown deadline

#### Scenario: OTLP exporter unavailable
- **GIVEN** an OTLP endpoint times out or returns an error
- **WHEN** the CLI completes analysis
- **THEN** export is bounded and the failure is recorded only as a safe diagnostic
- **AND** telemetry failure does not change a successful analysis into a failed one or mask the original failure

#### Scenario: Sensitive input is present
- **GIVEN** issue text, code, spec content, or credentials are available to the process
- **WHEN** spans, metrics, or export errors are produced
- **THEN** the content and credential values are absent
- **AND** metric dimensions contain only bounded values

#### Scenario: No model operation exists
- **GIVEN** the current Pathfinder command runs without invoking a model
- **WHEN** telemetry is emitted
- **THEN** it does not emit GenAI token, model, or cost measurements
- **AND** product usage reports model metering as unavailable/not metered

#### Scenario: Measured stage telemetry is persisted for aggregation
- **GIVEN** a Pathfinder command completes one or more instrumented stages
- **WHEN** it writes its lean job record
- **THEN** the record includes only fixed stage/outcome counts and measured duration aggregates
- **AND** it includes no trace IDs, span IDs, issue/run identifiers, source content, or error text in those telemetry fields
- **AND** the metrics are available even when no external OTLP endpoint is configured
