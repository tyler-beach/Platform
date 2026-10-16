# Proposal: define the first implementation-ready vertical slice

## Why

The repository contains a target architecture and broad contracts, but implementation can still diverge because the first user journey, decision boundaries, concrete labeled examples and proof obligations are spread across separate documents. The next phase should establish one reviewable slice before production code is written.

## What changes

- Specify the first bounded comparison: one versioned code change against one known accepted ADR.
- Define expected dispositions for supported deviation, no deviation found, not applicable and inconclusive evidence.
- Require immutable source references, evidence validation, an explicit applicability decision, bounded model usage and a human-reviewed result.
- Create synthetic evaluation examples and map critical requirements to test/evaluation proof.
- Clarify which product/runtime/security decisions require explicit approval before implementation or pilot.

## Scope

This change is a behavioral proposal and readiness plan. It may add OpenSpec requirements, decision tables, synthetic fixtures and traceability documentation.

## Non-goals

- Implementing Go services, workers, adapters, database migrations or generated runtime code.
- Deploying AWS resources or calling Anthropic.
- Implementing all three comparison modes or broad format support.
- Selecting numeric model cost/latency thresholds without owner approval and workload evidence.
- Enabling automatic merge blocking, ADR mutation or repository writes based on AI findings.

## Acceptance criteria

- The first slice and its non-goals can be explained without inferring unstated behavior.
- Every requirement added by this change has observable Given/When/Then scenarios.
- Synthetic cases define expected outcome, applicability and acceptable evidence.
- The critical proof matrix maps every P0/P1 risk to a planned test/evaluation and gate.
- Blocking decisions are either explicitly approved or remain visible as blockers.
- Implementation tasks remain unchecked until code/tests actually exist and evidence is reviewed.
