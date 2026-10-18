# Adversarial grill: github-actions-go-pathfinder

**Method:** `docs/ADVERSARIAL_DESIGN_REVIEW.md` + `docs/FUNCTIONAL_CORE.md` (no `grillme` skill installed in this environment).  
**Date:** 2026-10-18  
**Status:** Design grill before implementation; findings must be resolved in specs/design or explicitly deferred.

## Executive grill verdict

Direction is sound for an Actions-only production slice: Go pure core, staged jobs as worker boundaries, schema parity, fail-closed intake. The original proposal under-specified **publication idempotency**, **artifact poisoning between stages**, **budget/timeouts for extraction**, and **identity of “who may trigger analyze.”** Those are addressed below and reflected in design/spec revisions.

## Grill findings

| ID | Severity | Failure mode | Resolution |
|----|----------|--------------|------------|
| G1 | P0 | Duplicate issue comments on re-run / race | Spec: concurrency + update-by-marker comment semantics |
| G2 | P0 | Stage B trusts Stage A artifact from wrong run | Design: artifact names include `github.run_id` + `run_attempt`; concurrency cancel-in-progress |
| G3 | P1 | Workflow outputs leak source | Spec: no source in outputs/summaries |
| G4 | P1 | Schema-valid but wrong-version evidence accepted | Core must validate evidence IDs/revisions/paths like Python collector; covered by collector fail-closed scenario |
| G5 | P1 | Paste extractor DoS (huge issue body) | **Added:** soft size caps on tech_spec/code fields; reject with error comment when exceeded (see design amendment below) |
| G6 | P1 | Python left as silent fallback → dual brains | Spec: production MUST NOT call Python evaluate entrypoints |
| G7 | P2 | Fingerprint drift (map order, float) | Canonical JSON helper + golden `report_sha256` tests |
| G8 | P2 | “Exactly-once” language creep | Proposal/non-goals: at-least-once + idempotent publish only |
| G9 | P2 | Monolithic Go binary recreates Python blob | Design: package boundaries + stage-specific commands preferred |
| G10 | Defer | Cross-tenant / authz on issue body | Public GitHub Issues trust model; no multi-tenant cloud API in scope — deferred with AWS |
| G11 | Defer | Cumulative model spend | No model calls on this path — N/A until AI stage exists |
| G12 | Defer | DB+workflow dual-write | No DB; Actions artifacts only — N/A |

## Functional-core grill

- [x] Pure evaluation over explicit package + catalog snapshots
- [x] No hidden network in `internal/engine`
- [x] Outcomes ≠ execution errors
- [x] Canonical sort before fingerprint
- [x] Effects (`gh`, FS) only in cmd/issueintake shell
- [x] Stage outputs treated as immutable once written to artifact

## Spec amendments from grill

1. Design already includes comment marker update — keep as normative in actions-stage-orchestration (done).
2. Add input size limits to design (below) and a scenario under go-pathfinder-runtime.
3. Artifact naming must include run identity (design amendment).

## Design amendments (normative)

### Input size limits

CLI/intake MUST reject when decoded tech_spec or any code blob exceeds configured caps (initial defaults: 256 KiB tech_spec, 256 KiB per code file, 1 MiB total package JSON). Rejection produces error `comment.md`, exit 2, no invented observations.

### Artifact identity

Uploaded stage artifacts MUST be named with `github.run_id` and `github.run_attempt` (already pattern in current workflow) and consumed only by jobs in the same workflow run.

## Remaining accepted risks

- GitHub API comment update may fail; fallback create is allowed once per publish attempt with marker present check best-effort.
- Paste heuristics remain incomplete vs full NL; silence ≠ compliance (existing product rule).
- Companion change required for PR URL / multi-file remote inputs.
