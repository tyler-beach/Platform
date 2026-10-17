# API response mockups: production-target contract

> **Mock API responses · synthetic data.** These examples are shaped to the current production-target REST/JSON contract in `docs/openapi.yaml`, mapped from `proto/adrplatform/v1/platform.proto`. They are deterministic mockups for product and engineering review, not responses captured from a running service. Identifiers, timestamps, digests, and source references are synthetic.

## 1. Create an analysis job

`POST /v1/workspaces/ws_example/analysis-jobs`

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

### Mock response — HTTP 202 Accepted

This body follows `CreateAnalysisJobResponse` and `AnalysisJob`. The HTTP status communicates asynchronous acceptance; the body is the contract-shaped response.

~~~~json
{
  "job": {
    "jobId": "job_01JAXAMPLE482",
    "workspaceId": "ws_example",
    "comparisonMode": "COMPARISON_MODE_SPECIFICATION_TO_IMPLEMENTATION",
    "status": "ANALYSIS_JOB_STATUS_QUEUED",
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
    "createdAt": "2026-10-17T23:30:00Z",
    "updatedAt": "2026-10-17T23:30:00Z",
    "pipelineVersion": "pathfinder-pipeline-example-1",
    "correlationId": "ci-pr-482"
  },
  "reusedExistingJob": false
}
~~~~

The server accepts durable work and returns promptly. A queued job is not evidence that analysis succeeded or that a deviation exists. A retry using the same idempotency key and canonical request can return the same logical job with `reusedExistingJob: true`.

## 2. Read the job lifecycle

`GET /v1/workspaces/ws_example/analysis-jobs/job_01JAXAMPLE482`

### Mock response — HTTP 200

~~~~json
{
  "job": {
    "jobId": "job_01JAXAMPLE482",
    "workspaceId": "ws_example",
    "comparisonMode": "COMPARISON_MODE_SPECIFICATION_TO_IMPLEMENTATION",
    "status": "ANALYSIS_JOB_STATUS_SUCCEEDED",
    "inputArtifacts": [
      {
        "artifactId": "spec_session_service",
        "artifactVersionId": "spec_revision_12",
        "kind": "ARTIFACT_KIND_TECHNICAL_SPECIFICATION",
        "sourceUri": "repo://session-service/docs/session-service-spec.md",
        "contentSha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "revision": "12"
      }
    ],
    "createdAt": "2026-10-17T23:30:00Z",
    "updatedAt": "2026-10-17T23:30:18Z",
    "pipelineVersion": "pathfinder-pipeline-example-1",
    "correlationId": "ci-pr-482"
  }
}
~~~~

The current typed contract keeps job lifecycle separate from finding outcomes. Result counts are obtained by listing findings rather than inventing a `resultSummary` field on `AnalysisJob`.

## 3. List findings

`GET /v1/workspaces/ws_example/analysis-jobs/job_01JAXAMPLE482/findings?pageSize=20`

### Mock response — HTTP 200

~~~~json
{
  "findings": [
    {
      "findingId": "fnd_ses_005_pdb_minavailable",
      "jobId": "job_01JAXAMPLE482",
      "outcome": "FINDING_OUTCOME_DEVIATION_SUPPORTED",
      "severity": "FINDING_SEVERITY_HIGH",
      "reviewStatus": "REVIEW_STATUS_PENDING",
      "claim": "The supplied PodDisruptionBudget conflicts with ADR-002.",
      "rationale": "The supplied PDB sets minAvailable to 2, while the accepted decision specifies minAvailable: 1. This may block voluntary disruption when only two replicas are available; it does not by itself prove an outage.",
      "decisionIds": ["ADR-002"],
      "requirementIds": ["SES-005"],
      "evidence": [
        {
          "evidenceId": "ev_pdb_001",
          "artifactId": "deploy_session_pdb",
          "artifactVersionId": "git_9c4c0d8",
          "sourceUri": "repo://session-service/deploy/session/pdb.yaml",
          "path": "deploy/session/pdb.yaml",
          "startLine": 8,
          "endLine": 10,
          "symbolOrSection": "PodDisruptionBudget.spec",
          "excerptSha256": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
        },
        {
          "evidenceId": "ev_adr_002",
          "artifactId": "adr_session_availability",
          "artifactVersionId": "adr_002_v3",
          "sourceUri": "repo://session-service/docs/adr/ADR-002.md",
          "path": "docs/adr/ADR-002.md",
          "startLine": 14,
          "endLine": 16,
          "symbolOrSection": "Decision",
          "excerptSha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        }
      ],
      "humanReviewRequired": true,
      "validationStatus": "VALIDATED",
      "findingFingerprint": "sha256:example-pdb-policy-fingerprint",
      "createdAt": "2026-10-17T23:30:16Z"
    },
    {
      "findingId": "fnd_ses_009_revocation_ttl",
      "jobId": "job_01JAXAMPLE482",
      "outcome": "FINDING_OUTCOME_INCONCLUSIVE",
      "severity": "FINDING_SEVERITY_UNSPECIFIED",
      "reviewStatus": "REVIEW_STATUS_NEEDS_MORE_EVIDENCE",
      "claim": "The 60-second revocation propagation bound cannot be verified.",
      "rationale": "A revocation cache is present in the supplied source, but the immutable cache TTL configuration and timing test are absent. Presence of a cache does not establish the required bound.",
      "decisionIds": ["ADR-001"],
      "requirementIds": ["SES-009"],
      "evidence": [
        {
          "evidenceId": "ev_revocation_cache",
          "artifactId": "src_revocation_cache",
          "artifactVersionId": "git_9c4c0d8",
          "sourceUri": "repo://session-service/src/session/revocation_cache.go",
          "path": "src/session/revocation_cache.go",
          "startLine": 30,
          "endLine": 54,
          "symbolOrSection": "RevocationCache",
          "excerptSha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        }
      ],
      "humanReviewRequired": true,
      "validationStatus": "INCONCLUSIVE",
      "findingFingerprint": "sha256:example-revocation-fingerprint",
      "createdAt": "2026-10-17T23:30:17Z"
    }
  ],
  "nextPageToken": ""
}
~~~~

The response follows the current `Finding` and `EvidenceRef` contract: evidence references carry immutable artifact-version identity and source locators, while finding outcome, severity, review state, and validation status remain separate dimensions. The response intentionally does not embed source excerpts; authorized source retrieval is a separate concern.

## 4. Get one finding

`GET /v1/workspaces/ws_example/findings/fnd_ses_005_pdb_minavailable`

### Mock response — HTTP 200

~~~~json
{
  "finding": {
    "findingId": "fnd_ses_005_pdb_minavailable",
    "jobId": "job_01JAXAMPLE482",
    "outcome": "FINDING_OUTCOME_DEVIATION_SUPPORTED",
    "severity": "FINDING_SEVERITY_HIGH",
    "reviewStatus": "REVIEW_STATUS_PENDING",
    "claim": "The supplied PodDisruptionBudget conflicts with ADR-002.",
    "rationale": "The supplied PDB sets minAvailable to 2, while the accepted decision specifies minAvailable: 1.",
    "decisionIds": ["ADR-002"],
    "requirementIds": ["SES-005"],
    "evidence": [
      {
        "evidenceId": "ev_pdb_001",
        "artifactId": "deploy_session_pdb",
        "artifactVersionId": "git_9c4c0d8",
        "sourceUri": "repo://session-service/deploy/session/pdb.yaml",
        "path": "deploy/session/pdb.yaml",
        "startLine": 8,
        "endLine": 10,
        "symbolOrSection": "PodDisruptionBudget.spec",
        "excerptSha256": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
      }
    ],
    "humanReviewRequired": true,
    "validationStatus": "VALIDATED",
    "findingFingerprint": "sha256:example-pdb-policy-fingerprint",
    "createdAt": "2026-10-17T23:30:16Z"
  }
}
~~~~

## 5. Stable error payload

HTTP 409 when an idempotency key is reused with a different canonical request. This follows the existing OpenAPI `Problem` schema and RFC 9457-style fields.

~~~~json
{
  "type": "https://example.invalid/problems/conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "The idempotency key was used for a different request.",
  "instance": "/v1/workspaces/ws_example/analysis-jobs",
  "code": "IDEMPOTENCY_KEY_REUSED",
  "requestId": "req_01JAXAMPLE5",
  "retryable": false
}
~~~~

## 6. Contract behavior represented by the mockups

- The Protobuf service contract is the typed source of truth; the OpenAPI file maps it to REST/JSON.
- These mock responses are intended to guide the production implementation. They are not captured from a running API server.
- Field names and enum strings in these examples match the current OpenAPI/Protobuf model; schema validation in CI remains the enforcement mechanism.
- Job execution status is not a finding outcome. A successful job can contain aligned results, deviations, potential deviations, and inconclusive findings.
- A finding cites immutable evidence references. A URI does not grant access; each source dereference must be separately authorized.
