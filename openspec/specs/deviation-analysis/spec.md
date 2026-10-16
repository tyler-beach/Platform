# Deviation analysis

## Purpose
Compare implementation, technical specifications and architectural decisions to produce evidence-grounded assessments.

## Requirements

### Requirement: Comparison modes are distinct
The system MUST distinguish implementation-to-ADR, specification-to-ADR and specification-to-implementation comparisons.

#### Scenario: Implementation versus ADR
- GIVEN a versioned code change and candidate accepted ADR
- WHEN analysis runs
- THEN the result states supported deviation, no deviation found, or inconclusive
- AND includes decision version and implementation evidence used.

#### Scenario: Specification versus ADR
- GIVEN a specification and candidate decisions
- WHEN analysis runs
- THEN relevant constraints are compared with requirement passages
- AND the result references exact specification and decision evidence.

#### Scenario: Specification versus implementation
- GIVEN extracted requirements and a versioned implementation
- WHEN analysis runs
- THEN it identifies supported matches, conflicts and unverified requirements
- AND does not equate missing evidence with non-compliance or compliance.

### Requirement: Applicability precedes deviation judgment
The system MUST establish or explicitly mark uncertain the applicability of a decision before treating a conflict as a deviation.

#### Scenario: Candidate ADR is out of scope
- GIVEN a decision applies to a different service/environment
- WHEN it is retrieved because of textual similarity
- THEN it is excluded as a binding constraint or marked unresolved
- AND similarity alone does not create a confirmed deviation.

#### Scenario: Applicability is ambiguous
- GIVEN metadata and relationships do not establish scope
- WHEN assessment cannot resolve applicability
- THEN the result is inconclusive or requires review
- AND identifies missing applicability evidence.

### Requirement: Findings retain valid evidence
Every actionable finding MUST cite source-backed evidence.

#### Scenario: Unknown evidence reference
- GIVEN a model result cites an ID not supplied in its evidence package or a mismatched version
- WHEN validation runs
- THEN the candidate is rejected or made inconclusive
- AND is not published as a validated deviation.

### Requirement: Outcome and severity are distinct
The system MUST represent outcome, severity, confidence/quality evidence and review status separately.

#### Scenario: Confidence is high but impact is low
- GIVEN a well-supported low-impact deviation
- WHEN the finding is stored
- THEN model confidence does not automatically raise severity.

#### Scenario: Insufficient evidence
- GIVEN evidence cannot support a reliable conclusion
- WHEN analysis ends
- THEN the result explicitly says inconclusive/insufficient evidence
- AND does not fabricate a no-deviation result.
