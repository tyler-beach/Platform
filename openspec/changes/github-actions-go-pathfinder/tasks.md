## 1. Specs and grill

- [x] 1.1 Proposal, design, delta specs for go-pathfinder-runtime, actions-stage-orchestration, issue-package-evaluation
- [x] 1.2 Adversarial grill (`GRILL.md`) against ADVERSARIAL_DESIGN_REVIEW + FUNCTIONAL_CORE; revise specs/design
- [x] 1.3 `openspec validate github-actions-go-pathfinder --strict`

## 2. Go core (TDD)

- [x] 2.1 Module scaffold `go/pathfinder` + `canonical`/`fingerprint` helpers
- [x] 2.2 `internal/engine` table tests for kinds and outcomes (RED → GREEN)
- [x] 2.3 Catalog + predicate loaders with approved-only filter
- [x] 2.4 Package collector validation (fail closed)
- [x] 2.5 Paste `ensure_observations` tests (sample + fixtures); Python AST approximated
- [x] 2.6 `evaluate` aggregate + stable `report_sha256` on sample package
- [x] 2.7 Issue intake + comment render tests (no source echo; marker present)

## 3. CLI and workflow wiring

- [x] 3.1 `cmd/pathfinder-issue-analyze` preserving flags/exit/artifacts
- [x] 3.2 `cmd/pathfinder-evaluate-package` for local/docs parity
- [x] 3.3 Staged reusable workflow `pathfinder-go-analyze.yml` + update `pathfinder-issue-analyze.yml`
- [x] 3.4 Comment marker update semantics + concurrency retained
- [x] 3.5 CI job: `.github/workflows/pathfinder-go.yml` (`go test` + fixture dry-run)
- [x] 3.6 Docs: ISSUE_ANALYZE_WORKFLOW notes Go + Actions stages; AWS deferred

## 4. Job ledger (grill M1)

- [x] 4.1 Lean `job.json` writer + tests
- [x] 4.2 Ledger job on `pathfinder-jobs` with concurrency + retry + soft-fail
- [x] 4.3 OpenSpec `pathfinder-job-ledger` + `DECISIONS.md` from grill-me

## 5. Verification

- [x] 5.1 Focused Go tests green (`go test ./...` in `go/pathfinder`)
- [x] 5.2 Local CLI against fixture bodies produces comment/report/job.json
- [ ] 5.3 Workflow validates / PR CI green (pending push/PR)
- [ ] 5.4 Completion report after merge; archive OpenSpec when acceptance done
