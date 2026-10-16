# Secure AI execution

## Purpose
AI calls are bounded and treated as untrusted computation over authorized evidence.

## Requirements

### Requirement: Model calls are bounded and versioned
Every model operation MUST have a named purpose, versioned prompt/schema, explicit budget and deadline.

#### Scenario: Evidence package is oversized
- GIVEN the evidence package exceeds configured count/size/token limits
- WHEN a request is prepared
- THEN a deterministic prioritization/truncation/rejection policy is applied
- AND context is never sent unbounded.

#### Scenario: Provider call fails
- GIVEN an upstream failure
- WHEN the harness classifies it
- THEN it retries only within policy or returns a typed failure
- AND the overall job budget remains bounded.

### Requirement: Model output is validated before use
The system MUST validate response structure and evidence references before treating a result as actionable.

#### Scenario: Model invents evidence ID
- GIVEN a response cites an ID not in the supplied evidence package
- WHEN validation runs
- THEN the candidate is rejected or made inconclusive
- AND is not published as a validated finding.

#### Scenario: Output is valid JSON but unsupported
- GIVEN schema-valid output makes an unsupported claim
- WHEN application verification finds no supporting evidence
- THEN syntactic validity is not accepted as truth
- AND the inconclusive/review policy is applied.

### Requirement: Imported content is untrusted
The system MUST treat source artifacts and retrieval passages as data, not as instructions to the model or application.

#### Scenario: Source contains prompt injection
- GIVEN a code comment or spec tells the model to disclose secrets or ignore policy
- WHEN included in an evidence package
- THEN it remains untrusted data
- AND cannot authorize tools, retrieve secrets, change workflow routing or bypass validation.

### Requirement: AI-only destructive mutation is prohibited
The system MUST NOT let a model finding alone modify an ADR, write repository code or change production infrastructure.

#### Scenario: High-impact finding
- GIVEN a model reports a high-impact deviation
- WHEN the result is processed
- THEN evidence and review state are recorded
- AND follow-up mutation needs an explicitly authorized workflow.
