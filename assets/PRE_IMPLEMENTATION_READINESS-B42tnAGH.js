const e=`# Pre-implementation readiness

**Milestone:** Pre-Implementation Readiness  
**Status:** In progress — design/specification/test-data work only  
**Scope:** Prepare the first vertical slice for implementation review. No production service, application code, infrastructure, or runtime behavior is delivered by this milestone.

## Purpose

The repository already describes the target architecture and many cross-cutting controls. This milestone converts that material into a bounded first-release contract, a decision register that distinguishes recommendations from approvals, a concrete synthetic evaluation corpus, and traceable proof obligations.

A document or checklist being present is not evidence that the proposed runtime behavior exists. All runtime guarantees below remain requirements until demonstrated by implementation and test/evaluation evidence.

## Target first slice

Given one versioned code change and one known accepted ADR, the platform should:

1. Authenticate and authorize the caller and every referenced artifact.
2. Pin the exact code and ADR versions used for analysis.
3. Establish whether the ADR applies before judging a deviation.
4. Assemble deterministic, source-located evidence and identify missing required evidence.
5. Run a bounded, versioned model assessment only when policy allows it.
6. Validate the result and every cited evidence reference in application logic.
7. Persist a reviewable result, provenance and run metadata.
8. Report a supported deviation, no deviation found, or inconclusive outcome without treating missing evidence as proof of compliance.
9. Recheck freshness and review policy before any future external publication. External merge blocking is out of scope.

The first slice does not require all three comparison modes, every file format, semantic/vector search, automatic remediation, or a production GitHub comment/check integration.

## Readiness gates

Each gate is **not started**, **in progress**, or **ready for review** only when the listed evidence is linked. No gate is automatically considered complete because its documentation exists.

| Gate | Required outcome | Evidence to attach | Current posture |
|---|---|---|---|
| G0 — Product boundary | One input shape, one comparison mode, one reviewer workflow and explicit non-goals | Approved entries in the [MVP decision packet](MVP_DECISION_PACKET.md); vertical-slice OpenSpec review | In progress |
| G1 — Contract readiness | Inputs, outputs, source-version semantics, dispositions, authorization, errors, idempotency and stale-source behavior agree across contracts | Cross-document review; no unresolved contradictions in API, data, evidence and OpenSpec contracts | Not started |
| G2 — Quality readiness | A representative synthetic baseline exists with expected outcomes and acceptable evidence; quality metrics are defined | [Starter corpus](evaluation/STARTER_CORPUS.md), labeling guide and approved scoring protocol | In progress |
| G3 — Reliability and security readiness | Dispatch, replay, budget, cancellation, tenancy, source-data and model-output controls have testable scenarios | [Requirements-to-proof matrix](REQUIREMENT_TO_PROOF_MATRIX.md), reviewed fault/security test plan | In progress |
| G4 — Pilot readiness | A named owner approves the data-processing policy, operational ceilings, review process, rollback and release criteria | Decision log, security approval, test/evaluation report and pilot runbook | Not started |

## Definition of ready for implementation

Before implementation begins on the vertical slice:

- [ ] MVP decision packet has an owner-approved disposition for every decision marked as blocking.
- [ ] The vertical-slice OpenSpec proposal and scenarios are reviewed; unclear behavior is resolved or explicitly deferred.
- [ ] API, data, evidence, lifecycle and error contracts do not disagree about the same behavior.
- [ ] Synthetic corpus cases have stable IDs, self-contained inputs, expected outcomes and rationale.
- [ ] Each P0/P1 risk in the proof matrix maps to at least one planned test or evaluation and a release gate.
- [ ] Data sent to the direct Anthropic API is covered by an explicit approved policy before proprietary content is used.
- [ ] Initial cost, deadline, call/retry and concurrency limits have named approvers and configurable ownership; values are not guessed in code.
- [ ] The deployment/API profile and workflow-start recovery design are chosen or specifically excluded from the first slice.
- [ ] OpenSpec validation, documentation build, contract/schema checks and applicable CI gates have a documented owner.

These criteria permit implementation to be planned. They do not assert that a deployment is production-ready.

## Definition of done for this milestone

- [ ] Decision recommendations are clearly marked as recommendations until approved.
- [ ] OpenSpec scenarios are validated and reviewed.
- [ ] Corpus cases are synthetic and safe to commit; labels and expected evidence are independently reviewed.
- [ ] Requirement-to-proof mappings are reviewed, with no unowned P0/P1 item.
- [ ] README and documentation navigation point to this readiness package.
- [ ] PR CI passes; any checks that cannot run are explicitly recorded as not run.

## Scope boundary

This milestone intentionally adds no Go application implementation, generated server code, infrastructure, real provider calls, credentials, proprietary source snippets, or claims of production behavior. It makes the next implementation phase narrower and independently reviewable.

## Related artifacts

- [MVP decision packet](MVP_DECISION_PACKET.md)
- [Requirement-to-proof matrix](REQUIREMENT_TO_PROOF_MATRIX.md)
- [Evaluation corpus guide](evaluation/README.md)
- [Starter corpus](evaluation/STARTER_CORPUS.md)
- [Vertical-slice OpenSpec proposal](https://github.com/tyler-beach/Platform/blob/main/openspec/changes/mvp-vertical-slice/proposal.md)
- [Implementation roadmap](ROADMAP.md)
- [Open questions](OPEN_QUESTIONS.md)
`;export{e as default};
