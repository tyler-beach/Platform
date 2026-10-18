# Proposal: Real ADR catalog applicability

## Why

Pathfinder analyze on GitHub now runs Go end-to-end (paste + same-repo PR) against a **synthetic** 100-ADR catalog. That proves the spine, but real-org use needs versioned ADRs with applicability filtering so out-of-scope decisions do not silently look like coverage.

## What Changes

- Introduce an ADR catalog source (initially repo-checked markdown + typed requirement rows derived from accepted ADRs) with immutable version/hash per ADR.
- Applicability stage before kind evaluation: lifecycle-active + metadata filters (repo/service/domain/language as available); no match → `not_applicable` / `no_applicable_adr`, never “aligned.”
- Keep synthetic catalog available as a labeled demo mode; production default becomes real-catalog when configured.
- Preserve fail-closed evidence rules and advisory-only publication (no merge blocking in this change).

## Capabilities

### New Capabilities
- `adr-applicability`: Select applicable ADR requirement versions for a pinned package before evaluation.

### Modified Capabilities
- `issue-package-evaluation`: Evaluation MUST use applicability-filtered real or explicitly selected demo catalog; reports MUST identify catalog identity and version.

## Non-goals

- Vector retrieval / embeddings as the first cut (deterministic metadata filters first)
- AWS-hosted ADR store
- Automatic ADR mutation from findings
- Claiming adjudicated quality for model-mapped requirements

## Depends on

- Shipped Go Pathfinder runtime + PR adapter on Actions
