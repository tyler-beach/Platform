const e=`# MVP decision packet

**Status:** Proposed recommendations for review; not approved enterprise architecture decisions.  
**Purpose:** Close the decisions that would otherwise cause the first implementation to guess about scope, trust, cost, or deployment.

Record the decision owner, approver, date, rationale, alternatives and related ADR/OpenSpec change when a status changes. A recommendation is not an accepted decision until reviewed and recorded.

## Recommended defaults for the first slice

| ID | Decision | Recommended default | Why | Status / required action |
|---|---|---|---|---|
| MVP-D01 | First comparison mode | Implementation change ↔ one known, accepted ADR | Smallest useful version of the stated value proposition; aligns with the existing initial acceptance target | **Proposed.** Product/architecture owner to approve or amend |
| MVP-D02 | Initial change source | A pinned, immutable code diff/change snapshot; keep provider-specific ingestion behind an adapter | Enables deterministic fixtures before committing to a source-control integration | **Proposed.** Confirm whether snapshot input is sufficient for pilot |
| MVP-D03 | ADR source | One explicitly identified ADR with status, scope and immutable version/hash | Avoids building broad ADR discovery before applicability and provenance work | **Proposed.** Name the authoritative ADR source and lifecycle rules |
| MVP-D04 | Result policy | Advisory-only; human review for ambiguous/high-impact findings; no AI-only merge blocking | Prevents an unvalidated finding from becoming an enforcement decision | **Recommended baseline.** Any exception needs explicit approval |
| MVP-D05 | API exposure | Use the smallest ingress that serves the actual first consumer; prefer HTTP/Lambda if no synchronous gRPC consumer is demonstrated | Avoids funding a long-lived gRPC service before a real client need is established | **Blocking choice.** Review against the proposed Protobuf contract and real consumer |
| MVP-D06 | Async ownership | Step Functions owns asynchronous lifecycle; database remains the durable business record | Avoids competing sources of truth for retries, cancellation and terminal state | **Recommended.** Confirm workflow mode after latency/replay requirements are measured |
| MVP-D07 | Model provider | Direct Anthropic API through a narrow adapter; no Bedrock path | Matches the project's confirmed provider direction while isolating provider-specific details | **Direction confirmed;** organization data-processing approval remains required |
| MVP-D08 | Authoritative storage | PostgreSQL/Aurora for job, provenance, finding, budget and review metadata; object storage only where artifact size/lifecycle requires it | Provides durable constraints and queryable business state without premature specialized stores | **Recommended.** Confirm operational platform and migration ownership |
| MVP-D09 | Evaluation data | Synthetic fixtures first; no proprietary source until approved for model use and retention | Enables baseline coverage without exposing protected source material | **Proposed policy.** Security/data owner to approve before pilot |
| MVP-D10 | Release posture | Shadow/advisory pilot with freshness checks, rollback and human disposition | Collects quality evidence before any enforcement decisions | **Recommended.** Product and security owner to approve entry/exit criteria |

## Decisions that must not be guessed

The following values or policy choices affect real spend, authorization, data handling or reliability. Keep them explicitly open until an owner approves them.

| Area | Decision required | Acceptable completion evidence |
|---|---|---|
| Data processing | Which code/spec/ADR content may be sent to Anthropic; retention, region, logging and deletion requirements | Written data/security approval linked from the decision log |
| Tenant model | Single-workspace pilot or multi-workspace from day one; membership source and authorization boundary | Threat model and approved tenant contract |
| Initial operating limits | Per-call input/output, cumulative job spend/token/call/retry/deadline, workspace/global concurrency | Versioned configuration policy with named cost/operations owner |
| Unknown provider usage | Conservative charge and reconciliation/escalation for timed-out or ambiguous attempts | Approved accounting policy and corresponding test scenarios |
| Workflow semantics | Standard versus Express Step Functions; maximum duration, recovery, visibility and duplicate semantics | Measured workload assumptions and signed architecture decision |
| Dispatch recovery | Transactional outbox versus database dispatch table with lease, fencing and reconciliation | Failure-state diagram and test plan; choice validated against selected database |
| Source freshness | What must be rechecked before result display, review or future publication | Product contract distinguishing historical truth from current source state |
| Retention | Snapshots, evidence excerpts, model request/response metadata, budget ledger, audits and review records | Retention table with deletion and legal-hold behavior |
| API consumer | Whether a genuine long-lived gRPC consumer exists in MVP | Named consumer and documented hosting trade-off, or explicit HTTP/Lambda decision |
| Quality gate | Minimum evidence-validity and reviewer-approved quality needed for shadow/pilot; no arbitrary numeric threshold yet | Baseline run, label review, owner-approved threshold and override process |

## Approval record

Use one record per decision:

- **Decision ID:**
- **Status:** proposed / accepted / rejected / deferred
- **Decision owner / approver:**
- **Date:**
- **Chosen option:**
- **Alternatives considered:**
- **Rationale and consequences:**
- **Follow-up actions / risks:**
- **Related issue, ADR or OpenSpec change:**

A deferred decision must include the event that will force it to be revisited. Do not mark a decision accepted merely because its recommended option appears in this document.
`;export{e as default};
