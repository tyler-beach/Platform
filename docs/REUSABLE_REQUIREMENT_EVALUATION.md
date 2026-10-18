# Reusable ADR Requirement Evaluation

## Decision

The session TTL evaluator is a vertical slice for proving evidence integrity, deterministic evaluation, and conservative outcomes. It is not the architecture to copy once per ADR.

The platform should separate five concerns:

1. **Applicability and retrieval** — identify potentially applicable ADRs using accepted status, scope metadata, repository/service ownership, dependency context, and retrieval from the ADR store.
2. **Requirement normalization** — turn ADR prose into a typed, versioned requirement candidate. Preserve the source ADR, exact text span, model/prompt version if AI was used, and human approval state. A model proposes structure; validation decides whether the structure is usable.
3. **Evidence collection** — technology-specific collectors inspect code, configuration, deployment manifests, cloud state, tests, runtime telemetry, or dependency relationships. Collectors emit common normalized observations with source revision/hash and source locator.
4. **Shared evaluation** — deterministic handlers implement reusable requirement kinds rather than individual ADR IDs.
5. **Common result contract** — all outcomes include applicability, evidence IDs, provenance, rationale, uncertainty, policy/engine versions, and a deterministic fingerprint.

## Initial requirement kinds

| Kind | Meaning | Example |
|---|---|---|
| `numeric_max` | observed numeric property must not exceed a threshold | session TTL <= 600 seconds |
| `resource_present` | required resource/property must exist | workload has a PodDisruptionBudget |
| `boolean_required` | security property must be enabled | encryption at rest enabled |
| `set_membership` | configured value must belong to an approved set | approved TLS policy |
| `dependency_forbidden` | a relationship must not exist | service must not call a restricted system |
| `coverage_required` | every in-scope entity must have evidence/property | all public routes have auth middleware |

These are candidate types, not a promise that every natural-language ADR can be safely reduced to one simple predicate. Composite or ambiguous requirements should remain unnormalized or inconclusive until supported.

## Shared observation contract

An observation should carry at least: `evidence_id`, typed `predicate`, `subject`, typed `value`, `artifact_id`, immutable `revision`, repository-relative `path`, source SHA-256, and a typed locator (AST span, JSON Pointer, YAML resource, API object, test, or trace). Values must be checked against their declared types; Python booleans must not be accepted as integers.

The generic engine prototype at `.poc/requirement_engine/engine.py` accepts normalized evidence and demonstrates two distinct requirement kinds. It does **not** parse Kubernetes YAML or arbitrary ADR prose. A real Kubernetes collector must establish whether a PDB exists and whether it applies to the intended workload; a missing collector result is not proof of a missing PDB.

## Outcome semantics

- `supported_deviation`: applicable requirement, sufficient accepted evidence, deterministic predicate is violated.
- `no_deviation_found`: applicable requirement, sufficient accepted evidence for the evaluated scope; not a universal proof of compliance.
- `not_applicable`: applicability gate says the ADR does not apply; do not claim compliance.
- `inconclusive`: missing, malformed, conflicting, stale, or insufficient evidence, or requirement semantics are unsupported.

A collector that did not run, could not parse a manifest, or cannot determine workload ownership must report an evidence gap. It must not synthesize a negative observation.

## AI and deterministic boundaries

Use retrieval and AI to find candidate ADRs and propose normalized requirements when language is ambiguous. Validate the proposed structure against a versioned schema and preserve provenance. Use deterministic handlers for numeric comparisons, resource presence, boolean properties, set membership, and graph constraints when the observation semantics are explicit. AI may assist with semantic mapping or triage, but should not manufacture source evidence or silently convert uncertainty into a confident result.

## Validation sequence

1. Harden the TTL evidence/result contract and pass exact-head CI.
2. Demonstrate the same common result semantics on a second, structurally different kind: PDB resource presence.
3. Add a real manifest collector with positive, negative, multi-namespace, selector/workload association, malformed-input, and missing-collector cases.
4. Expand requirement kinds only when corpus examples demonstrate a reusable semantic family.
5. Keep integration to Aurora/Bedrock, repository events, and production systems out of this offline prototype until contracts and evaluation quality are validated.
