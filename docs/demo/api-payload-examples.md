# API payload examples: analysis jobs and findings

> **Design-only examples.** The REST/JSON API is proposed in docs/openapi.yaml; no production HTTP service is deployed by this site. IDs, timestamps, hashes, URLs, and results are synthetic. These examples illustrate intended semantics; fields must be reconciled against proto/adrplatform/v1/platform.proto and the OpenAPI schema before implementation.

## 1. Submit an analysis job

POST /v1/workspaces/ws_example/analysis-jobs

~~~~json
{
  "workspaceId": "ws_example",
  "idempotencyKey": "pr-482-head-9c4c0d8",
  "comparisonMode": "COMPARISON_MODE_SPECIFICATION_TO_IMPLEMENTATION",
  "inputArtifacts": [
    {
      "artifactId": "spec_session_service",
      "artifactVersionId": "spec_revision_12",
      "kind": "ARTIFACT_KIND_TECHNICAL_SPECIFICATION",
      "sourceUri": "repo://session-service/docs/session-service-spec.md",
      "contentSha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "revision": "12"
    },
    {
      "artifactId": "adr_session_ttl",
      "artifactVersionId": "adr_001_v3",
      "kind": "ARTIFACT_KIND_ADR",
      "sourceUri": "repo://session-service/docs/adr/ADR-001.md",
      "contentSha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "revision": "3"
    },
    {
      "artifactId": "session_change",
      "artifactVersionId": "git_9c4c0d8",
      "kind": "ARTIFACT_KIND_CODE_CHANGE",
      "sourceUri": "https://github.com/example/session-service/pull/482",
      "contentSha256": "89abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "revision": "9c4c0d8"
    }
  ],
  "correlationId": "ci-pr-482"
}
~~~~

### Accepted response — HTTP 202

~~~~json
{
  "job": {
    "jobId": "job_01JAXAMPLE482",
    "workspaceId": "ws_example",
    "state": "JOB_STATE_QUEUED",
    "comparisonMode": "COMPARISON_MODE_SPECIFICATION_TO_IMPLEMENTATION",
    "createdAt": "2026-10-17T23:30:00Z",
    "updatedAt": "2026-10-17T23:30:00Z",
    "correlationId": "ci-pr-482"
  },
  "reusedExistingJob": false,
  "polling": {
    "href": "/v1/workspaces/ws_example/analysis-jobs/job_01JAXAMPLE482",
    "recommendedAfterMs": 1500
  },
  "requestId": "req_01JAXAMPLE"
}
~~~~

Acceptance means the request was validated and durable work accepted for asynchronous processing. It does not mean analysis completed or that a deviation exists.

## 2. Read the job lifecycle

GET /v1/workspaces/ws_example/analysis-jobs/job_01JAXAMPLE482

~~~~json
{
  "job": {
    "jobId": "job_01JAXAMPLE482",
    "workspaceId": "ws_example",
    "state": "JOB_STATE_SUCCEEDED",
    "comparisonMode": "COMPARISON_MODE_SPECIFICATION_TO_IMPLEMENTATION",
    "createdAt": "2026-10-17T23:30:00Z",
    "updatedAt": "2026-10-17T23:30:18Z",
    "startedAt": "2026-10-17T23:30:02Z",
    "completedAt": "2026-10-17T23:30:18Z",
    "correlationId": "ci-pr-482",
    "resultSummary": {
      "findingsCount": 9,
      "supportedDeviationCount": 2,
      "noDeviationFoundCount": 3,
      "inconclusiveCount": 2,
      "potentialDeviationCount": 2
    }
  },
  "requestId": "req_01JAXAMPLE2"
}
~~~~

**Contract note:** exact summary fields and whether potential findings are an outcome or review status must be aligned with the Protobuf and OpenAPI schemas before implementation. This example makes proposed semantics visible; it is not a generated response from a running service.

## 3. List findings

GET /v1/workspaces/ws_example/analysis-jobs/job_01JAXAMPLE482/findings?pageSize=20

~~~~json
{
  "findings": [
    {
      "findingId": "fnd_ses_005_pdb_minavailable",
      "requirementId": "SES-005",
      "decisionId": "ADR-002",
      "outcome": "FINDING_OUTCOME_SUPPORTED_DEVIATION",
      "severity": "SEVERITY_HIGH",
      "title": "PDB requires both replicas to remain available",
      "summary": "The supplied PDB sets minAvailable to 2 while the accepted decision specifies minAvailable: 1.",
      "evidenceRefs": [
        {
          "evidenceId": "ev_pdb_001",
          "artifactId": "deploy_session_pdb",
          "artifactVersionId": "git_9c4c0d8",
          "contentSha256": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
          "path": "deploy/session/pdb.yaml",
          "locator": { "kind": "LINE_RANGE", "startLine": 8, "endLine": 10 },
          "evidenceClass": "EVIDENCE_CLASS_CONFIGURATION_OBSERVATION",
          "excerpt": "minAvailable: 2"
        },
        {
          "evidenceId": "ev_adr_002",
          "artifactId": "adr_session_availability",
          "artifactVersionId": "adr_002_v3",
          "path": "docs/adr/ADR-002.md",
          "locator": { "kind": "LINE_RANGE", "startLine": 14, "endLine": 16 },
          "evidenceClass": "EVIDENCE_CLASS_DECISION_STATEMENT",
          "excerpt": "Set minAvailable: 1."
        }
      ],
      "limitations": [
        "Synthetic fixture; no live cluster was inspected.",
        "The configuration contradiction does not prove an outage."
      ],
      "review": { "status": "REVIEW_STATUS_PENDING", "required": true }
    },
    {
      "findingId": "fnd_ses_006_sync_provider",
      "requirementId": "SES-006",
      "decisionId": "ADR-003",
      "outcome": "FINDING_OUTCOME_SUPPORTED_DEVIATION",
      "severity": "SEVERITY_HIGH",
      "title": "Request handler waits for external risk scoring",
      "summary": "The handler awaits the provider before returning, contrary to the asynchronous decision.",
      "evidenceRefs": [
        {
          "evidenceId": "ev_handler_006",
          "artifactId": "src_session_handler",
          "artifactVersionId": "git_9c4c0d8",
          "path": "src/session/handler.go",
          "locator": { "kind": "LINE_RANGE", "startLine": 72, "endLine": 79 },
          "evidenceClass": "EVIDENCE_CLASS_STATIC_CODE_OBSERVATION",
          "excerpt": "riskClient.Score(ctx, request)"
        }
      ],
      "limitations": ["Static call-path evidence; runtime latency was not measured."],
      "review": { "status": "REVIEW_STATUS_PENDING", "required": true }
    }
  ],
  "nextPageToken": "",
  "requestId": "req_01JAXAMPLE3"
}
~~~~

## 4. Inconclusive is a first-class outcome

GET /v1/workspaces/ws_example/findings/fnd_ses_009_revocation_ttl

~~~~json
{
  "finding": {
    "findingId": "fnd_ses_009_revocation_ttl",
    "requirementId": "SES-009",
    "outcome": "FINDING_OUTCOME_INCONCLUSIVE",
    "severity": "SEVERITY_UNSPECIFIED",
    "title": "Revocation propagation bound cannot be verified",
    "summary": "The source includes a revocation cache, but the immutable configuration and timing test required to verify the 60-second bound were not supplied.",
    "evidenceRefs": [
      {
        "evidenceId": "ev_revocation_cache",
        "artifactId": "src_revocation_cache",
        "artifactVersionId": "git_9c4c0d8",
        "path": "src/session/revocation_cache.go",
        "locator": { "kind": "LINE_RANGE", "startLine": 30, "endLine": 54 },
        "evidenceClass": "EVIDENCE_CLASS_STATIC_CODE_OBSERVATION",
        "excerpt": "cache lookup and invalidation logic"
      }
    ],
    "missingEvidence": [
      { "expectedKind": "configuration", "reason": "Cache TTL configuration is absent." },
      { "expectedKind": "test_result", "reason": "No integration test measures revocation propagation time." }
    ],
    "review": { "status": "REVIEW_STATUS_NEEDS_EVIDENCE", "required": true }
  },
  "requestId": "req_01JAXAMPLE4"
}
~~~~

## 5. Stable error payload

HTTP 409 for reuse of an idempotency key with a different canonical request:

~~~~json
{
  "type": "https://example.invalid/problems/idempotency-key-reused",
  "title": "Idempotency key already used",
  "status": 409,
  "detail": "The key was previously used with a different request body.",
  "instance": "/v1/workspaces/ws_example/analysis-jobs",
  "code": "IDEMPOTENCY_KEY_REUSED",
  "requestId": "req_01JAXAMPLE5",
  "retryable": false
}
~~~~

This follows RFC 9457 Problem Details conventions. Production errors must not expose cross-tenant resource existence or sensitive source contents.

## 6. Contract and implementation cautions

- Payloads are illustrative, not generated by a deployed server.
- The authoritative typed contract is proto/adrplatform/v1/platform.proto; docs/openapi.yaml is the proposed REST mapping.
- Before implementation, align every field and enum with the schemas and generate transport types rather than maintaining parallel DTOs by hand.
- Job execution state and finding outcome are separate: a successful job may contain deviations, alignments, and inconclusive results.
- A finding cites immutable evidence references; clients must not treat excerpts as standalone proof or dereference artifact URIs without authorization.
~~~~
