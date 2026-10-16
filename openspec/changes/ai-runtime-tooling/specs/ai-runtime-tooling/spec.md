# AI runtime tooling

## Purpose
Run AI-assisted deviation analysis through a bounded, testable harness whose source data, findings and model execution are observable and reviewable.

## Requirements

### Requirement: AI requests are bounded and versioned
The system MUST issue model requests through a defined operation contract with explicit limits and version metadata.

#### Scenario: Assessment is executed
- GIVEN a job evidence package and a named analysis operation
- WHEN an Anthropic API request is created
- THEN the system records the prompt/schema/pipeline version and evidence IDs
- AND enforces a request deadline and configured input/output/call budget.

#### Scenario: Evidence exceeds the budget
- GIVEN a requested evidence package exceeds policy limits
- WHEN the harness prepares a model request
- THEN it follows a deterministic prioritization, truncation or rejection policy
- AND does not make an unbounded call.

### Requirement: AI findings are validated by the application
The system MUST validate model output independently of its syntactic format before treating the result as actionable.

#### Scenario: Model returns a valid schema with an unknown reference
- GIVEN the response conforms to its schema but cites evidence not provided to the job
- WHEN application validation runs
- THEN the finding is rejected or marked inconclusive
- AND cannot be published as a validated deviation.

#### Scenario: Required evidence is missing
- GIVEN available artifacts do not support a conclusion
- WHEN assessment completes
- THEN the result identifies insufficient evidence
- AND does not infer that no deviation exists.

### Requirement: AI behavior changes have regression evaluations
The system MUST maintain versioned evaluation cases for model-dependent behavior and run applicable evaluations when prompts, models, retrieval, parsers or finding semantics change.

#### Scenario: Prompt is changed
- GIVEN a prompt or model configuration changes
- WHEN the change is proposed for merge
- THEN the relevant labeled regression suite runs or the skip is explicitly documented and approved
- AND the result is available for review before rollout.

### Requirement: Telemetry protects source content
The system MUST correlate model and retrieval operations with analysis jobs while excluding secrets and full source payloads from standard telemetry.

#### Scenario: Model invocation is traced
- GIVEN an Anthropic request is made
- WHEN telemetry is emitted
- THEN the trace includes operation/model/prompt version, latency, usage and validation metadata where available
- AND raw source excerpts, credentials and unredacted prompt/response bodies are not recorded by default.

### Requirement: Agent frameworks and memory products need justification
The system MUST NOT require a dedicated memory platform or agent orchestration framework unless an approved requirement and evaluation demonstrate a material benefit.

#### Scenario: A framework is proposed
- GIVEN a proposal to add an agent framework, memory system, graph database, vector backend or hosted evaluation product
- WHEN the proposal is reviewed
- THEN it states the concrete problem, alternatives, operational/data-security cost, evaluation plan and removal path
- AND preserves the authoritative source-version/provenance model.
