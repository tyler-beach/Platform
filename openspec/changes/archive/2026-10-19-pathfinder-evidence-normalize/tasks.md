## 1. OpenSpec

- [x] 1.1 Write proposal, design, delta spec, and tasks for evidence normalize.
- [x] 1.2 Validate the change with OpenSpec CLI.

## 2. Tests first

- [x] 2.1 Add failing Go tests for locator precision derivation (exact / approximate / unavailable).
- [x] 2.2 Add failing Go tests for canonical sort stability under shuffled input.
- [x] 2.3 Add failing Go tests for conflict classification (conflict vs agree).
- [x] 2.4 Add collect-adapter regression that unknown predicates still fail closed and normalized observations carry precision.

## 3. Implementation

- [x] 3.1 Implement `internal/evidence` pure normalize, precision, sort, and conflict helpers.
- [x] 3.2 Wire `pkgcollect.CollectObservations` through the evidence package without synthesizing observations.
- [x] 3.3 Run focused Go tests and record results.

## 4. Verification

- [x] 4.1 `go test ./...` under `go/pathfinder`.
- [x] 4.2 `openspec validate pathfinder-evidence-normalize`.
- [x] 4.3 Confirm no secrets/source excerpts are logged by the new package.
