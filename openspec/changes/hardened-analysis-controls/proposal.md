# Proposal: Harden distributed and AI execution controls

## Why

The current architecture has the right major direction—evidence-first analysis, Step Functions for asynchronous orchestration, a functional core in Go, and a bounded Anthropic harness—but some core reliability and cost controls are recommendations rather than explicit behavioral contracts.

The highest-risk gaps are the database/workflow-start dual-write failure, cumulative token/spend across retries and parallel calls, duplicate external effects, and lack of a repeatable mapping from behavior scenarios to tests/evaluation evidence.

## What changes

- Require a durable dispatch intent and reconciliation mechanism for accepted jobs.
- Require idempotent logical effects under at-least-once event delivery and worker replay.
- Require atomic or otherwise concurrency-safe cumulative model-budget reservation and per-attempt usage reconciliation.
- Require job-wide token, cost, call/retry and deadline ceilings across assessment, repair and optional verification.
- Require explicit behavioral scenario → test/evaluation evidence traceability for implementation changes.
- Codify functional core / imperative shell, canonicalization, immutable stage handoff and effect boundaries as reviewable acceptance criteria.

## Scope and non-goals

In scope: behavioral contracts, distributed retry/replay safety, AI budget accounting, and engineering workflow gates.

Out of scope: implementing the production service, selecting exact price/limit values, resolving API hosting/authentication, selecting Step Functions Standard versus Express, choosing a final outbox mechanism, or enabling automatic merge blocking. Those decisions need consumer, security and operational evidence.

## Acceptance criteria

- Each added requirement has observable Given/When/Then scenarios.
- The design names failure-injection and concurrency tests for dispatch, idempotency and budget enforcement.
- Model output never authorizes access or becomes actionable without independent application validation.
- The OpenSpec proposal remains active until implementation tests/evaluations pass and current-state specs can be reconciled.
