# Plan: gaps → Go brains → Actions orchestration

## Target (this phase)

Provide tech spec / code (issue package or paste now; PR/files next) → structured ADR deviation report **inside GitHub**, with **Go** owning evaluation brains and **Actions reusable workflows** simulating worker stages. **AWS out of scope.**

## Gap backlog (ordered)

| # | Gap | Change | Status |
|---|-----|--------|--------|
| 1 | Brains in Python | `github-actions-go-pathfinder` | Implementing |
| 2 | Monolithic Actions job | same (staged workflows) | Spec’d |
| 3 | Comment duplication / races | same (marker update + concurrency) | Spec’d |
| 4 | PR URL / multi-file remote | `github-input-adapters` | Spec’d; blocked on #1 |
| 5 | Real org ADR store + retrieval | future | Out of phase |
| 6 | Model-backed semantic mapping | future | Out of phase |
| 7 | AWS SFN/Lambda | future | Explicitly deferred |

## Delivery sequence

1. OpenSpec + grill (done for both changes).
2. TDD Go `internal/engine` → collectors → paste → evaluate → issue CLI.
3. Wire monolithic Go CLI into `pathfinder-issue-analyze.yml`.
4. Split reusable stage workflows; preserve E2E comment+artifact.
5. Implement `github-input-adapters` on top of Go intake.
6. Archive OpenSpecs only after acceptance tests/CI green.

## Proof style

- Unit/table-driven for pure core (RED→GREEN).
- Fixture/behavioral tests for issue bodies and sample packages.
- Workflow CI as functional proof of the Actions backbone.
