# pathfinder-otel Specification

## Purpose
Define optional privacy-preserving OpenTelemetry instrumentation for Go Pathfinder commands in GitHub Actions.

## Requirements
### Requirement: Export bounded Pathfinder telemetry over optional OTLP

Pathfinder analysis commands MUST emit traces and low-cardinality operational metrics through OpenTelemetry when `OTEL_EXPORTER_OTLP_ENDPOINT` is configured. OTLP/HTTP export MUST be opt-in, bounded by export and shutdown deadlines, and non-blocking to the analysis result. Without an endpoint, telemetry MUST use no-op providers. Spans and metrics MUST NOT record source content, issue bodies, prompts, evidence excerpts, secrets, or unbounded identifiers. Metric labels MUST be normalized to fixed stage/outcome values.

#### Scenario: Endpoint is not configured
- **GIVEN** a Pathfinder command runs without an OTLP endpoint
- **WHEN** it performs analysis
- **THEN** analysis output and exit status are unchanged
- **AND** no network export is attempted

#### Scenario: Endpoint is configured
- **GIVEN** an administrator configures an OTLP/HTTP endpoint
- **WHEN** issue analysis or package evaluation runs
- **THEN** a root trace and fixed-name stage spans are emitted
- **AND** stage run/duration and terminal result metrics use bounded dimensions

#### Scenario: Collector is unavailable
- **GIVEN** the collector delays, rejects, or cannot accept telemetry
- **WHEN** the analysis command shuts down
- **THEN** exports and flush are bounded and report only a generic redacted warning
- **AND** telemetry failure does not change the analysis result

#### Scenario: Sensitive inputs are available
- **GIVEN** source, issue content, evidence, or credentials exist in process memory
- **WHEN** telemetry is recorded
- **THEN** those values and dynamic identifiers are absent from span attributes and metric labels

#### Scenario: The PoC has no model call
- **GIVEN** current Pathfinder analysis does not invoke a model
- **WHEN** telemetry is emitted
- **THEN** no GenAI token, model, or spend metrics are fabricated

#### Scenario: Measured stage metrics are retained for the dashboard
- **GIVEN** instrumented stages run in a Pathfinder CLI invocation
- **WHEN** the CLI writes its lean job record
- **THEN** it includes fixed-stage counts and measured duration aggregates without dynamic identifiers or content
- **AND** this local aggregate is available whether or not OTLP export is configured
