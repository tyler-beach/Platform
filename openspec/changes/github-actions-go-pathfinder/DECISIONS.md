# Grill-me decisions (shared understanding)

Source: grill-me rounds 1–6 (2026-10-18). Stateless interview; this file records commitments for OpenSpec/impl.

## Product bar

| ID | Decision |
|----|----------|
| Q1 | Production bar = usable for real org work on GitHub **and** portable toward a later AWS shell (dual). |
| Q2 | Day-to-day surface = Pathfinder analyze **issues** (maintainers/collaborators). |
| Q3 | Synthetic catalog OK; keep `synthetic_unadjudicated` labels. |
| Q4/Q15 | Python `.poc` evaluate remains forever as **offline oracle**; production workflow MUST NOT call it. |
| Q5 | Keep/amend existing Go direction. |
| Q6 | Ship on Actions for real use; Go core contracts stay portable for AWS later. |
| Q7 | Trust boundary = single GitHub repo/org (no multi-tenant product yet). |
| Q9 | Advisory only; no merge blocking from findings. |
| Q10 | Phase success = collaborator outside the builder set can use it unaided (after M2). |
| Q13 | “Outsider” = repo collaborator; issue form + docs; Pages optional prep. |

## Milestones

| Milestone | Scope |
|-----------|--------|
| **M1** (this change) | Go spine + staged Actions + comment marker updates + **`pathfinder-jobs` ledger** |
| **M2** (`github-input-adapters`) | Same-repo PR changed-files adapter (multi-file via PR only); tech-spec optional |

Q16=B: two merges; do not claim Q10 until M2.

## Job ledger (M1)

| ID | Decision |
|----|----------|
| Q8/Q11 | JSONL (or JSON lines) on branch `pathfinder-jobs`. |
| Q12 | Lean index: job_id, issue, run_id/attempt, fingerprints, aggregate status, timestamps, engine version; full report in Actions artifacts only. |
| Q17 | `GITHUB_TOKEN` + `contents: write` on analyze workflow only; machine commits to `pathfinder-jobs`, not `main`. |
| Q18 | If ledger fails after successful evaluate: still comment; soft-fail / retry ledger. |
| Q26 | Serialize ledger writes (`concurrency`) **and** fetch→append→commit retry on reject. |

## Portable core

| ID | Decision |
|----|----------|
| Q23 | Unit of work: `EvidencePackage` → `EvaluationReport`; workflow passes IDs/artifact refs only (no source in outputs). |

## Deferred / out of scope

- AWS deploy, multi-tenant control plane, real ADR store, model-backed mapping, merge blocking, fork PRs, issue multi-file bundles/zips, expanding Pages for adapters.
