# Example technical specification: Session Management Service

> **Synthetic demonstration artifact.** Requirements, source references, finding IDs, hashes, and results are illustrative. They do not describe a live service or a production analysis result.

## 1. Purpose and scope

The Session Management Service issues, validates, refreshes, and revokes user sessions for internal APIs. This example demonstrates comparison across architecture decisions, plain-English requirements, source/configuration evidence, and change diffs.

**System boundary:** API gateway, session API, signing component, session store, asynchronous maintenance worker, Kubernetes deployment, and CI workflow.

**Out of scope:** identity proofing, upstream identity-provider availability, browser storage, and authorization decisions after authentication.

## 2. Normative requirements

MUST/MUST NOT indicate normative constraints; SHOULD indicates a reviewed default that may require a documented exception.

| ID | Requirement | Verification target |
|---|---|---|
| SES-001 | An access session MUST have an absolute lifetime no greater than **10 minutes**. Refresh MUST NOT extend the original absolute expiry. | Token claims, session record, refresh path |
| SES-002 | Validation MUST reject expired, revoked, malformed, or incorrectly signed tokens before protected business logic executes. | Middleware and call path |
| SES-003 | Signing keys MUST be obtained through the approved secret-management boundary. Private signing material MUST NOT be committed or emitted in logs. | Configuration, secret references, logging |
| SES-004 | Session state changes MUST be auditable with actor/service identity, action, timestamp, and correlation ID; tokens and secrets MUST be excluded. | Event schema, write path, redaction |
| SES-005 | The service MUST remain available during a single pod disruption when at least two healthy replicas are available. Deployment settings MUST preserve at least one available replica. | Replicas, readiness, PDB, rollout |
| SES-006 | External risk scoring MUST execute asynchronously after request acceptance. The request path MUST return a durable job/session correlation ID without waiting for the provider. | Handler, dispatch intent, worker |
| SES-007 | Every API error MUST use a stable machine-readable code and request/correlation ID. | Error mapping and response schema |
| SES-008 | The service SHOULD enforce per-subject refresh rate limits and return a retry hint when throttled. | Rate-limit policy and response |
| SES-009 | Revocation MUST become effective for subsequent validation within **60 seconds**. | Cache TTL/invalidation, validation, tests |
| SES-010 | Readiness MUST be exposed separately from liveness and fail when required local dependencies are unusable. | Health handlers and deployment probes |

## 3. Architecture decisions

### ADR-001 — Bounded session lifetime
- **Decision:** access sessions have a maximum absolute lifetime of 10 minutes; refresh cannot move the original expiry.
- **Reason:** reduce the exposure window for stolen credentials.
- **Status:** Accepted.
- **Evidence expected:** decision record, token construction, refresh logic, tests.

### ADR-002 — Availability during voluntary disruption
- **Decision:** run at least two replicas in production and configure a PodDisruptionBudget with minAvailable: 1; readiness gates traffic.
- **Reason:** routine node maintenance must not intentionally evict all serving replicas.
- **Status:** Accepted.
- **Evidence expected:** deployment, PDB, readiness probe, rollout strategy.

### ADR-003 — Asynchronous external risk scoring
- **Decision:** request handlers persist or dispatch a durable work intent and return without waiting for external risk scoring.
- **Reason:** isolate request latency and provider failure from session issuance.
- **Status:** Accepted.
- **Evidence expected:** handler call graph, dispatch intent, queue/worker path, tests.

### ADR-004 — Secret boundary
- **Decision:** signing keys are retrieved through the approved secret manager; source configuration contains references, not key material.
- **Reason:** keep secret lifecycle and access policy outside the application artifact.
- **Status:** Accepted.
- **Evidence expected:** configuration schema, secret reference, deployment identity, redaction tests.

## 4. Example change under review

Change set PR-482, revision 9c4c0d8 (synthetic). It updates refresh handling, introduces a provider retry helper, adjusts Kubernetes deployment settings, and adds an audit event. Evidence is deliberately mixed: some requirements are supported, some contradicted, and some remain inconclusive because required artifacts are absent.

## 5. Assessment matrix

| Requirement | Example result | Evidence observed | What it supports | What it does not prove |
|---|---|---|---|---|
| SES-001 absolute TTL ≤ 10 minutes | **Aligned** | Token constructor sets expiry to issue time + 600 seconds; refresh preserves original expiry; tests cover 599/600/601 seconds. | Code and tests support the absolute bound. | Does not prove deployed configuration matches this revision or every issuance path is covered. |
| SES-002 reject invalid sessions before business logic | **Aligned** | Middleware validates signature, expiry, and revocation before the protected handler; integration test asserts handler is not called for invalid tokens. | Observed call order and test assertion support the gate. | Static analysis cannot prove every runtime route uses the middleware. |
| SES-003 approved secret boundary | **Aligned** | Deployment references a secret-manager entry; source uses a secret-manager client; redaction test checks token/key fields. | Source and configuration references are consistent with the ADR. | Does not prove IAM policy correctness or production secret population. |
| SES-004 audit without secrets | **Potential deviation** | Event includes actor, action, timestamp, and correlation ID, but one serializer path forwards authorization_header into details. | A reachable path appears capable of copying sensitive request metadata. | Does not establish the header contains a live token in every call or that downstream redaction never removes it. Human verification required. |
| SES-005 availability during one pod disruption | **Deviation** | Deployment specifies two replicas, but PDB uses minAvailable: 2. | PDB conflicts with the accepted minAvailable: 1 decision and requirement intent. | Does not prove an outage will occur; scheduling, readiness, rollout, and capacity also matter. |
| SES-006 asynchronous provider work | **Deviation** | Handler awaits riskClient.score() before returning; queue is used only for retry telemetry. | Request path waits for provider and conflicts with the decision. | Does not establish measured latency or outage frequency. |
| SES-007 stable API errors | **Aligned** | Error mapper emits code, requestId, and bounded message; schema test validates required fields. | Schema is consistent with the requirement. | Does not prove every proxy/edge error uses the mapper. |
| SES-008 refresh rate limit | **Inconclusive** | Rate-limit configuration exists, but the artifact binding it to the refresh route is absent. | A candidate policy exists to inspect. | Cannot establish the policy is active on the endpoint. |
| SES-009 revocation within 60 seconds | **Inconclusive** | Revocation cache code is present, but TTL configuration and integration timing test are missing. | A revocation mechanism exists in supplied source. | Cannot verify the 60-second bound without configuration and timing evidence. |
| SES-010 readiness separate from liveness | **Potential alignment** | Deployment has separate /health/live and /health/ready paths, but probe configuration and handlers come from different revisions. | Names suggest intended separation. | Version mismatch prevents a reliable cross-artifact conclusion. |

## 6. Evidence interpretation rules

1. **Alignment is scoped to supplied evidence.** It is not a universal claim that a system is compliant.
2. **Deviation requires a contradiction.** Missing files, unreachable code, unresolved dispatch, or unbound configuration should normally be inconclusive or potential—not silently treated as pass/fail.
3. **Separate observation from interpretation.** An observation records what was found at a version-bound location; a finding relates that observation to a requirement and explains the inference.
4. **Preserve counter-evidence.** For SES-004, retain both expected audit fields and the suspicious sensitive field.
5. **Do not treat model confidence as probability.** Scores are review-support signals unless calibrated and validated.
6. **Require human review for consequential decisions.** The system proposes a classification and rationale; an authorized engineer confirms, dismisses, or requests more evidence.

## 7. Example evidence-linked finding envelope

~~~~json
{
  "findingId": "fnd_ses_005_pdb_minavailable",
  "requirementId": "SES-005",
  "decisionId": "ADR-002",
  "outcome": "SUPPORTED_DEVIATION",
  "severity": "HIGH",
  "title": "PDB requires both replicas to remain available",
  "summary": "The supplied PDB sets minAvailable to 2 while the accepted decision specifies minAvailable: 1.",
  "evidenceRefs": [
    {
      "evidenceId": "ev_pdb_001",
      "artifactVersionId": "git:9c4c0d8",
      "path": "deploy/session/pdb.yaml",
      "locator": { "kind": "line", "start": 8, "end": 10 },
      "excerpt": "minAvailable: 2",
      "evidenceClass": "configuration_observation"
    },
    {
      "evidenceId": "ev_adr_002",
      "artifactVersionId": "adr:ADR-002:v3",
      "path": "docs/adr/ADR-002.md",
      "locator": { "kind": "line", "start": 14, "end": 16 },
      "excerpt": "Set minAvailable: 1.",
      "evidenceClass": "decision_statement"
    }
  ],
  "limitations": [
    "Synthetic example; no live cluster was assessed.",
    "The configuration contradiction does not prove an outage."
  ],
  "review": { "status": "PENDING_REVIEW", "required": true }
}
~~~~

## 8. Recommended reviewer actions

- **SES-004:** inspect serializer and redaction order; add a regression test proving authorization headers never reach audit storage.
- **SES-005:** confirm intended PDB value is minAvailable: 1; validate node-drain and rollout behavior.
- **SES-006:** move provider work behind durable asynchronous dispatch or revise ADR-003 through the normal decision process.
- **SES-008/009:** attach route binding and cache TTL/timing artifacts before classifying.
- **SES-010:** rerun against one immutable revision for both probe configuration and handlers.

This specification contains **3 aligned requirements, 2 supported deviations, 2 potential findings, and 2 inconclusive requirements**. This is a teaching aid, not a compliance score.
