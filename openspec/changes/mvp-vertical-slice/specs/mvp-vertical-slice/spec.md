# MVP vertical slice

## ADDED Requirements

### Requirement: First-slice analysis is bounded and evidence traceable

The first releasable analysis journey MUST compare one versioned implementation change with one known accepted architectural decision and MUST preserve explicit applicability, provenance, evidence validity and outcome semantics. This requirement defines the initial product boundary; it does not imply that runtime behavior has been implemented.

#### Scenario: Clear conflict with applicable accepted decision

- GIVEN a versioned code change and a known accepted ADR whose scope governs that change
- AND deterministic evidence supports a conflict with a stated ADR constraint
- WHEN the bounded analysis completes
- THEN the result may be reported as a supported deviation only with references to the exact ADR version and code revision
- AND every reference must resolve to the supplied evidence package
- AND the result remains advisory and reviewable.

#### Scenario: Sufficient evidence does not establish a conflict

- GIVEN a versioned code change and an applicable accepted ADR
- AND sufficient bounded evidence has been reviewed for the stated constraint
- WHEN no conflict is established
- THEN the result says no deviation found for that bounded comparison
- AND it does not claim universal compliance beyond the evidence and scope.

#### Scenario: The candidate decision does not govern the change

- GIVEN a candidate ADR whose authoritative status or scope establishes that it does not govern the analyzed component/revision
- WHEN applicability is resolved
- THEN the candidate is marked not applicable or excluded from binding assessment
- AND textual similarity alone does not create a deviation.

#### Scenario: Applicability or implementation evidence is insufficient

- GIVEN source metadata or call-path evidence is missing, ambiguous or contradictory
- WHEN a defensible conclusion cannot be reached
- THEN the result is inconclusive and identifies the missing evidence
- AND absence of evidence is not converted to a no-deviation result.

#### Scenario: Candidate finding cites unknown or mismatched evidence

- GIVEN a model candidate references a missing evidence ID, invalid locator or different source version
- WHEN application-side validation runs
- THEN the candidate is rejected or made inconclusive
- AND it cannot be persisted or published as a validated deviation.

#### Scenario: Source changes before external publication

- GIVEN a finding was produced from pinned source revision A
- AND the current source has advanced to revision B
- WHEN an external publication is requested
- THEN the finding retains its historical links to A
- AND the publication policy checks freshness and declines or clearly marks a stale result according to approved policy.

#### Scenario: Duplicate admission request

- GIVEN an admission request has the same idempotency identity and same canonical request fingerprint as an existing job
- WHEN it is submitted again
- THEN the platform returns or resolves the same logical job without duplicate logical effects
- AND reuse of the idempotency identity for a materially different request follows a documented conflict behavior.

#### Scenario: Model budget is exhausted

- GIVEN cumulative job token, spend, call or deadline allowance has been reserved or consumed by earlier attempts
- WHEN another assessment, repair, retry or verification call is considered
- THEN the call is not admitted if the applicable budget cannot be reserved
- AND the job returns a typed exhaustion/review outcome without resetting consumed allowance.
