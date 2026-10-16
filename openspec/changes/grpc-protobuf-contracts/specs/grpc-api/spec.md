# gRPC platform API

## Purpose
Expose typed control-plane operations for asynchronous analysis jobs and evidence-backed findings.

## ADDED Requirements

### Requirement: Analysis creation is asynchronous and idempotent
The platform API MUST create or resolve a job using an idempotency key and return a job identifier without holding the RPC open for the full analysis.

#### Scenario: New job accepted
- GIVEN an authenticated caller authorized for all referenced artifacts
- WHEN CreateAnalysisJob receives a valid request with idempotency key and comparison mode
- THEN the service creates a job and schedules workflow execution
- AND returns job ID/status without waiting for final findings.

#### Scenario: Duplicate create request
- GIVEN a logically identical request has already been accepted with the same idempotency identity
- WHEN the caller retries CreateAnalysisJob
- THEN the service returns the existing logical job or a documented idempotent response
- AND does not launch duplicate side effects.

### Requirement: Access is authorized server-side
The API MUST authorize the authenticated principal for the requested workspace, artifacts and findings.

#### Scenario: Unauthorized workspace selector
- GIVEN the caller is not authorized for the requested workspace
- WHEN a job or finding is requested
- THEN the service returns a permission error
- AND does not disclose protected artifact or finding existence.

### Requirement: Finding evidence is version-bound
The API MUST return findings with references to the exact artifact versions and locations used in assessment.

#### Scenario: Caller retrieves finding
- GIVEN the caller is authorized to read a finding
- WHEN GetFinding returns it
- THEN the response includes outcome, severity, review status and source-version-bound evidence references.

### Requirement: RPC execution is bounded
The server MUST apply deadlines, message-size and pagination limits, and documented status codes.

#### Scenario: Caller deadline expires
- GIVEN the caller's deadline expires before a synchronous operation completes
- WHEN processing observes cancellation
- THEN the server cancels safe in-flight work and does not claim the whole analysis was rolled back.

### Requirement: Protobuf API evolution is checked
The repository MUST lint/build Protobuf definitions and detect incompatible changes before merge.

#### Scenario: Incompatible field change is proposed
- GIVEN a change would alter a field's wire type or remove/renumber a field incompatibly
- WHEN schema CI runs
- THEN validation fails until compatibility is preserved or a reviewed breaking-version strategy is adopted.
