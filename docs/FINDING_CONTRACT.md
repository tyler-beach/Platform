# Finding and evidence contract

The canonical API shape is defined in `proto/adrplatform/v1/platform.proto`. This document records the invariants that consumers and future persistence adapters must enforce.

## Keep these states separate

- **Applicability** answers whether the ADR governs this subject and context: `in_scope`, `out_of_scope`, or `uncertain`.
- **Finding outcome** answers what the evidence establishes: supported deviation, potential deviation, no deviation found in reviewed evidence, or inconclusive.
- **Severity** describes impact; it is not confidence or evidence strength.
- **Review status** records a reviewer workflow state.
- **Adjudication status** records a separate authorized decision about a reviewer disposition.

Do not collapse these dimensions into a single status or score. In particular, `no_deviation_found` is not proof of universal compliance, and `out_of_scope` is not a compliance result.

## Required evidence invariants

1. Every evidence link must reference a requirement evidence ID and an observation evidence ID present in the same immutable evidence package.
2. Each referenced artifact version must be immutable and bound to a content hash or source revision wherever the source supports it.
3. A link's relationship is typed: supports, contradicts, contextual, or uncertain. The explanation must describe what the relationship establishes and what it does not.
4. Counter-evidence is first-class. A finding cannot omit known contradictory observations merely because they weaken the candidate claim.
5. The analysis version and canonical input fingerprint must be recorded so the assessment can be replayed.
6. Limitations must state missing runtime evidence, unresolved dispatch, stale locators, or other assumptions that affect the conclusion.
7. Unknown enum values, missing references, and cross-workspace references must fail validation rather than be silently coerced.

## Idempotency and replay

The input fingerprint should be computed from a documented canonical serialization of the immutable input artifact references, ADR versions, applicable policy version, and deterministic analysis configuration. It must not include volatile fields such as timestamps or generated display text.

Job creation must honor the client idempotency key. Finding deduplication should use a stable fingerprint scoped to the target, ADR version, policy/analysis version, and evidence snapshot. A replay against identical inputs should reproduce the same deterministic artifacts; a changed input must create a new analysis version rather than mutate old evidence.

## Privacy and authorization

Evidence references are not authorization grants. Every artifact and evidence lookup must independently enforce workspace/repository access. Public issue bodies and logs should contain only approved references and hashes, not source excerpts, prompts, secrets, or customer data.

## Prototype boundary

The schema defines a contract, not a deployed API. It does not prove that a server persists immutable versions, validates cross-reference integrity, enforces idempotency, or authorizes access. Those behaviors require implementation and integration tests before production use.
