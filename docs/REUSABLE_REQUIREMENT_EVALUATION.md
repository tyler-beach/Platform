# Reusable ADR Requirement Evaluation

## Decision

The session TTL evaluator is a vertical-slice **adapter** that proves evidence integrity and now decides through the shared engine. It is not the architecture to copy once per ADR.

The platform separates five concerns:

1. **Applicability and retrieval** — identify potentially applicable ADRs using accepted status, scope metadata, repository/service ownership, dependency context, and retrieval from the ADR store.
2. **Requirement normalization** — turn ADR prose into a typed, versioned requirement candidate. Preserve the source ADR, exact text span, model/prompt version if AI was used, and human approval state. A model may propose structure; validation and approval decide whether the structure is usable (`.poc/requirement_engine/normalize.py`).
3. **Evidence collection** — technology-specific collectors inspect code, configuration, deployment manifests, cloud state, tests, runtime telemetry, or dependency relationships. Collectors emit common normalized observations with source revision/hash and source locator. Collectors bind by **predicate capability** (`.poc/requirement_engine/predicate_registry.py`), not by ADR ID.
4. **Shared evaluation** — deterministic handlers implement reusable requirement kinds rather than individual ADR IDs (`.poc/requirement_engine/engine.py`).
5. **Common result contract** — all outcomes include applicability, evidence IDs, provenance, rationale, uncertainty, policy/engine versions, and a deterministic fingerprint.

## Scale rule

| Grows with ADR count | Must stay small |
|---|---|
| Approved typed requirements in a store | Collector implementations (by evidence domain) |
| Retrieval / applicability candidates | Kind handlers |
| Workflow topology / result schema | — |

New ADRs MUST reuse an existing kind + registered predicate whenever possible. Unknown predicates fail closed. Unsupported prose stays `unnormalized` or inconclusive — never a new `investigate_<adr>.py`.

## Multi-ADR catalog (synthetic)

`.poc/requirement_catalog/` contains **100** synthetic ADRs (`ADR-101`–`ADR-200`) with approved typed requirements and a predicate seed file. Label status is `synthetic_unadjudicated`.

Evaluate a tech-spec/code evidence package against the whole catalog (production CLI is Go; Python under `.poc` remains an offline oracle):

```sh
cd go/pathfinder
go build -o /tmp/pathfinder-evaluate-package ./cmd/pathfinder-evaluate-package
# Default: synthetic ADR-101–200
/tmp/pathfinder-evaluate-package \
  ../../.poc/requirement_catalog/sample_packages/multi-domain-session-service/package.json
# Opt-in real pack (docs/adr-derived rows under data/adr_catalog)
/tmp/pathfinder-evaluate-package --catalog-mode=real \
  ../../.poc/requirement_catalog/sample_packages/multi-domain-session-service/package.json
```

Per-requirement outcomes remain `supported_deviation`, `no_deviation_found`, `not_applicable`, or `inconclusive`. Aggregate status may be `mixed` (product language for partial alignment: some aligned, others deviant and/or inconclusive). Regenerate with `python3 .poc/requirement_catalog/generate_catalog.py`.

### GitHub Issue intake

Open a **Pathfinder analyze package** issue (public/synthetic content only). Provide a tech-spec, optional **same-repo pull request** (changed text files), and/or a single sample code snippet. A deterministic paste extractor (`paste_heuristic_v1`) fills allowlisted observations when you omit hand-written observation JSON. Go on Actions evaluates the catalog, comments aggregate status + outcome counts, uploads the full report artifact, and appends a lean job record on `pathfinder-jobs`. Unextracted predicates stay `inconclusive`. See `docs/ISSUE_ANALYZE_WORKFLOW.md`.

## Requirement kinds

| Kind | Meaning | Example |
|---|---|---|
| `numeric_max` | observed numeric property must not exceed a threshold | session TTL <= 600 seconds |
| `resource_present` | required resource/property must exist | workload has a PodDisruptionBudget |
| `boolean_required` | security property must be enabled | encryption at rest enabled |
| `set_membership` | configured value must belong to an approved set | approved TLS policy |
| `dependency_forbidden` | a relationship must not exist | service must not call a restricted system *(candidate)* |
| `coverage_required` | every in-scope entity must have evidence/property | all public routes have auth middleware *(candidate)* |

Kinds marked candidate are not implemented until corpus families justify them. Composite or ambiguous requirements remain unnormalized or inconclusive until supported.

## Predicate registry and collectors

Registered predicates declare value type, compatible kinds, and collector id:

- `config_json` — pinned JSON + JSON Pointer (session TTL, encryption flags, TLS policy ids)
- `kubernetes_manifest` — offline YAML inventory (PDB presence)

The PDB path uses `pdb_collector.py` through the Kubernetes capability. The TTL path validates pinned cases in `session_ttl/investigate.py` but decides with `engine.evaluate(kind=numeric_max)`.

## Shared observation contract

An observation should carry at least: `evidence_id`, typed `predicate`, `subject`, typed `value`, `artifact_id`, immutable `revision`, repository-relative `path`, source SHA-256, and a typed locator. Values must be checked against their declared types; Python booleans must not be accepted as integers.

## Outcome semantics

- `supported_deviation`: applicable requirement, sufficient accepted evidence, deterministic predicate is violated.
- `no_deviation_found`: applicable requirement, sufficient accepted evidence for the evaluated scope; not a universal proof of compliance.
- `not_applicable`: applicability gate says the ADR does not apply; do not claim compliance.
- `inconclusive`: missing, malformed, conflicting, stale, or insufficient evidence, or requirement semantics are unsupported.

A collector that did not run, could not parse a manifest, or cannot determine workload ownership must report an evidence gap. It must not synthesize a negative observation.

## AI and deterministic boundaries

Use retrieval and AI to find candidate ADRs and propose normalized requirements when language is ambiguous. Validate the proposed structure against the kind/predicate catalog and preserve provenance. Use deterministic handlers for numeric comparisons, resource presence, boolean properties, and set membership when observation semantics are explicit. AI may assist with semantic mapping or triage, but should not manufacture source evidence or silently convert uncertainty into a confident result.

## Validation sequence

1. Harden the TTL evidence/result contract and pass exact-head CI.
2. Demonstrate the same common result semantics on a second, structurally different kind: PDB resource presence.
3. Add a real manifest collector with positive, negative, multi-namespace, selector/workload association, malformed-input, and missing-collector cases.
4. Collapse TTL decisioning onto the shared engine; introduce predicate registry + normalizer.
5. Expand requirement kinds only when corpus examples demonstrate a reusable semantic family.
6. Keep integration to Aurora/Bedrock, repository events, and production systems out of this offline prototype until contracts and evaluation quality are validated.
