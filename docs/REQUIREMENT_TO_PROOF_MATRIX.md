# Requirements-to-proof matrix

**Status:** Initial review draft. This matrix is a plan for verification, not evidence that controls have been implemented or passed.  
**Use:** Link each requirement to an observable scenario, a planned proof method, an owner and a release gate. Update results only with actual test/evaluation artifacts.

## Release gates

- **PR:** deterministic checks expected for every relevant change.
- **Pre-pilot:** integration, security, fault-injection or baseline evaluation evidence required before pilot access.
- **Model/config release:** repeat the relevant corpus evaluation when model, prompt, schema, retrieval, parser or finding policy changes.
- **Approval:** organizational decision/policy evidence; tests alone cannot substitute.

## Core matrix

| ID / priority | Requirement or failure mode | Contract / source | Minimum proof required | Gate | Status |
|---|---|---|---|---|---|
| RP-01 / P0 | Accepted jobs cannot be lost between database commit and workflow start | [Operations](OPERATIONS.md); hardened-analysis-controls proposal | Fault-inject failure after transaction commit, before workflow start, after ambiguous start and before dispatch acknowledgement; reconciliation yields one logical execution | Pre-pilot | Planned |
| RP-02 / P0 | Duplicate submissions/events do not create duplicate logical work or external effects | [API contract](contracts/API_CONTRACT.md); [data contracts](contracts/CONTRACTS.md) | Same idempotency key + same canonical request reuses the logical job; key reuse for a different fingerprint has a documented conflict behavior; replay publication is idempotent | PR + pre-pilot | Planned |
| RP-03 / P0 | Every read/dereference/cancel/publish is authorized within the workspace | [Security](SECURITY.md); [data contracts](contracts/CONTRACTS.md) | Cross-workspace identifier substitution, forged URI, foreign artifact reference, pagination token and cancellation attempts are denied without data leakage | PR + pre-pilot | Planned |
| RP-04 / P0 | Cumulative model cost and execution limits apply across parallel branches, retries, repair and verification | [AI runtime](contracts/AI_RUNTIME.md); [AI pipeline](AI_PIPELINE.md) | Concurrent reservation boundary tests, full cumulative accounting, denied post-exhaustion call, provider usage reconciliation and ambiguous-usage behavior | PR + pre-pilot | Planned |
| RP-05 / P0 | A finding cannot be actionable without evidence from the exact source version | [Evidence contract](contracts/EVIDENCE.md); [deviation spec](../openspec/specs/deviation-analysis/spec.md) | Unknown ID, wrong artifact version, invalid locator and unsupported claim are rejected or become inconclusive; no validated publication follows | PR | Planned |
| RP-06 / P1 | Missing or failed required evidence is not silently presented as complete | [Orchestration spec](../openspec/specs/orchestration-and-reliability/spec.md) | Fail/timeout required versus optional branches; completeness metadata and terminal disposition match the policy | PR + pre-pilot | Planned |
| RP-07 / P1 | Source changes do not rewrite historical analysis or silently publish stale findings | [Artifact/provenance spec](../openspec/specs/artifact-and-provenance/spec.md) | Analyze version A, advance source to B, read historical result, then attempt publication; preserve A's provenance and apply freshness policy | PR + pre-pilot | Planned |
| RP-08 / P1 | Cancellation cannot be interpreted as rollback of already completed effects | [Operations](OPERATIONS.md); hardened-analysis-controls proposal | Race cancellation against persistence and publication; record accepted/completed status correctly and prevent stale worker commits with fencing/state checks | Pre-pilot | Planned |
| RP-09 / P1 | Source content cannot override system policy or obtain privileged tools/data | [Security](SECURITY.md); [secure AI spec](../openspec/specs/secure-ai-execution/spec.md) | Prompt injection in source comments/ADR/spec; verify no policy bypass, secret disclosure, unauthorized retrieval or unsafe effect | PR + pre-pilot | Planned |
| RP-10 / P1 | Schema validity is not confused with semantic correctness | [AI pipeline](AI_PIPELINE.md); [deviation spec](../openspec/specs/deviation-analysis/spec.md) | Schema-valid but fabricated, stale, out-of-scope or contradicted response is not accepted as a supported deviation | PR + model/config release | Planned |
| RP-11 / P1 | Retrieval and assessment quality are measured before model/prompt/policy changes roll out | [Evaluation strategy](EVALUATION.md); starter corpus | Run versioned labeled corpus; report outcome accuracy, evidence resolution/support, correct inconclusive rate, cost and latency; review errors | Model/config release | Planned |
| RP-12 / P1 | Logs and traces aid operations without becoming an uncontrolled source-data sink | [Logging and audit](contracts/LOGGING_AND_AUDIT.md); [security](SECURITY.md) | Sensitive-source redaction tests; verify correlation IDs, model/prompt/schema versions, token usage and audit events without raw proprietary content by default | PR + pre-pilot | Planned |
| RP-13 / P1 | No unvalidated AI finding is the sole basis for merge blocking or authoritative ADR mutation | [Project brief](PROJECT_BRIEF.md); [security](SECURITY.md) | Configuration/policy test and review of all external effect paths; advisory default and explicit human override | Pre-pilot approval | Planned |
| RP-14 / P2 | Stable evidence packaging makes comparisons reproducible for fixed inputs/policy | [AI pipeline](AI_PIPELINE.md); [AI runtime](contracts/AI_RUNTIME.md) | Stable-order property tests for evidence IDs and canonical request fingerprints; record model/prompt/schema/policy versions | PR | Planned |

## First-slice functional and evaluation proof

| Corpus case | Expected disposition | Primary proof |
|---|---|---|
| EVAL-001 — Clear synchronous-call conflict | Supported deviation with exact code and ADR evidence | Golden evaluation + citation validation |
| EVAL-002 — Compliant asynchronous refactor | No deviation found for the scoped requirement | Golden evaluation + counterexample review |
| EVAL-003 — Out-of-scope ADR | Excluded as non-applicable; no confirmed deviation | Applicability unit/property tests + golden evaluation |
| EVAL-004 — Insufficient implementation evidence | Inconclusive with missing evidence identified | Golden evaluation; verifies abstention |
| EVAL-005 — Prompt injection in source | Treated as untrusted data; no instruction/policy override | Security adversarial test + reviewer check |
| EVAL-006 — Fabricated or wrong-version citation | Reject or mark inconclusive; never validated/published | Semantic evidence validation test |

The starter cases are synthetic and describe expected behavior; they are not model-performance results. The labels should be reviewed before the corpus is treated as a release baseline.

## Evidence record template

For each proof, preserve:

- Requirement/scenario ID and code/spec revision under test.
- Test/evaluation command and environment where relevant.
- Pass/fail result with a link to CI logs or report.
- Fixture, policy, prompt/schema/model version identifiers where applicable.
- Any accepted deviation, limitation or skipped check, with owner and rationale.
- Follow-up action and release gate impacted.

Do not change **Planned** to **Passed** without actual, reproducible evidence. If a test is not yet executable because code does not exist, keep it planned and retain the scenario as an implementation obligation.
