const e=`# Evidence lineage walkthrough

> **Synthetic fixture.** Every identifier, digest, source span, timestamp, and disposition below is illustrative. This is a worked data-model example, not a production finding or output from a running service.

This walkthrough follows one claim from immutable inputs to a reviewer disposition. It complements the [session-service scenario](realistic-session-service.md), [API response mockups](api-payload-examples.md), and [finding review playbook](finding-review-playbook.md).

## Claim under review

**Requirement SES-001:** An access session MUST have an absolute lifetime no greater than 10 minutes, and refresh MUST NOT extend the original absolute expiry.

**Observed source:** the synthetic \`IssueAccessToken\` path sets expiry to 30 minutes after the current time.

**Initial outcome:** \`FINDING_OUTCOME_DEVIATION_SUPPORTED\` in this mock record. This outcome is scoped to the pinned source observation. It does not prove that the path is reachable in production, that the source is deployed, or that no downstream control changes the effective expiry.

## 1. Pin the input versions

A job must refer to immutable versions, not just branch names or mutable paths.

~~~json
{
  "jobId": "job_demo_1042",
  "workspaceId": "ws_example",
  "pipelineVersion": "pathfinder-demo-0.4.0",
  "inputs": [
    {
      "artifactId": "adr_session_ttl",
      "artifactVersionId": "adr_001_v3",
      "kind": "ARTIFACT_KIND_ADR",
      "revision": "3",
      "contentSha256": "1111111111111111111111111111111111111111111111111111111111111111"
    },
    {
      "artifactId": "session_spec",
      "artifactVersionId": "spec_revision_12",
      "kind": "ARTIFACT_KIND_TECHNICAL_SPECIFICATION",
      "revision": "12",
      "contentSha256": "2222222222222222222222222222222222222222222222222222222222222222"
    },
    {
      "artifactId": "session_source",
      "artifactVersionId": "git_9c4c0d8",
      "kind": "ARTIFACT_KIND_SOURCE_FILE",
      "revision": "9c4c0d8",
      "contentSha256": "3333333333333333333333333333333333333333333333333333333333333333"
    }
  ]
}
~~~

These hashes are placeholders for demonstrating field shape; they are not digests of real artifacts.

## 2. Record observations before making a claim

The internal \`EvidenceItem\` contract in [Evidence contract](../contracts/EVIDENCE.md) carries provenance and locator precision. The public API's \`EvidenceRef\` is intentionally narrower; it does not expose full source excerpts.

~~~json
[
  {
    "evidenceId": "ev_demo_req_001",
    "jobId": "job_demo_1042",
    "artifactId": "session_spec",
    "artifactVersionId": "spec_revision_12",
    "artifactKind": "TECHNICAL_SPECIFICATION",
    "path": "docs/session-service-spec.md",
    "startLine": 18,
    "endLine": 18,
    "locatorPrecision": "EXACT",
    "relationToClaim": "SUPPORTS",
    "retrievalMethod": "document-heading-and-requirement-id",
    "sourceIntegrity": "VERIFIED"
  },
  {
    "evidenceId": "ev_demo_code_044",
    "jobId": "job_demo_1042",
    "artifactId": "session_source",
    "artifactVersionId": "git_9c4c0d8",
    "artifactKind": "SOURCE_FILE",
    "path": "internal/session/token.go",
    "startLine": 44,
    "endLine": 46,
    "symbolOrSection": "IssueAccessToken",
    "locatorPrecision": "EXACT",
    "relationToClaim": "CONTRADICTS",
    "retrievalMethod": "language-ast-rule",
    "sourceIntegrity": "VERIFIED"
  }
]
~~~

The relationship is relative to the claim being assessed. It is not a universal label for the artifact: the same source span may support one claim and contradict another. The excerpt is omitted here to keep the example focused on references and metadata.

## 3. Emit a finding that points only to known evidence

~~~json
{
  "findingId": "fnd_demo_ttl_001",
  "jobId": "job_demo_1042",
  "requirementId": "SES-001",
  "outcome": "FINDING_OUTCOME_DEVIATION_SUPPORTED",
  "severity": "FINDING_SEVERITY_HIGH",
  "reviewStatus": "REVIEW_STATUS_PENDING",
  "summary": "Token expiry is computed as 30 minutes after issuance, exceeding the 10-minute absolute lifetime requirement.",
  "evidenceRefs": [
    {
      "evidenceId": "ev_demo_req_001",
      "artifactId": "session_spec",
      "artifactVersionId": "spec_revision_12",
      "path": "docs/session-service-spec.md",
      "startLine": 18,
      "endLine": 18
    },
    {
      "evidenceId": "ev_demo_code_044",
      "artifactId": "session_source",
      "artifactVersionId": "git_9c4c0d8",
      "path": "internal/session/token.go",
      "startLine": 44,
      "endLine": 46
    }
  ],
  "limitations": [
    "Source revision is synthetic and is not evidence of a deployed artifact.",
    "Reachability and effective runtime configuration were not established.",
    "Refresh-path behavior requires separate evidence."
  ]
}
~~~

Before persisting a finding, deterministic validation should confirm that every evidence ID exists in this job's evidence package, each version matches the pinned input snapshot, and each locator is valid for that version. Model output must not invent IDs, paths, line ranges, or revisions. Unknown references fail validation rather than being silently dropped.

## 4. Keep reviewer disposition separate from analysis outcome

The analysis outcome says what the evidence supports. A reviewer disposition records a human decision about what to do with it.

~~~json
{
  "auditEventId": "audit_demo_0007",
  "eventType": "finding.review.dispositioned",
  "timestamp": "2026-10-17T18:42:00Z",
  "actor": {
    "type": "user",
    "id": "user_demo_reviewer"
  },
  "target": {
    "kind": "finding",
    "id": "fnd_demo_ttl_001",
    "version": "1"
  },
  "action": "DEFER",
  "reasonCode": "RUNTIME_CONTEXT_REQUIRED",
  "rationale": "Confirm that the pinned source revision is deployed and inspect refresh behavior before final disposition.",
  "correlationId": "review_demo_1042"
}
~~~

This is a synthetic example aligned to the intent of the [logging and audit contract](../contracts/LOGGING_AND_AUDIT.md), not a claim that the event schema or API endpoint is already implemented.

## 5. Expected reviewer path

1. Open the exact requirement and source spans at the recorded versions.
2. Verify that the 30-minute expression governs the relevant access-token path.
3. Inspect refresh logic and any policy or configuration that could change the effective expiry.
4. Confirm deployment provenance if the question is about a running environment.
5. Choose a disposition and record the reason. A defer action must not silently rewrite the analysis outcome to aligned.

## Invariants worth testing

- A finding cannot reference evidence from a different job.
- Evidence references must resolve to the pinned artifact version.
- A stale or mismatched source digest is surfaced, not treated as verified.
- Line ranges are one-based, inclusive, and within source bounds.
- Missing evidence means inconclusive or a validation failure, not automatic compliance.
- Reviewer disposition, analysis outcome, and job execution status remain separate fields.
- Logs contain opaque identifiers and metadata, not raw source excerpts or secrets.

These invariants are suitable for deterministic contract tests before any model-assisted assessment runs.
`;export{e as default};
