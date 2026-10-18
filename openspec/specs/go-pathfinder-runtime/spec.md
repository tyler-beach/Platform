# go-pathfinder-runtime Specification

## Purpose
Go-owned deterministic Pathfinder evaluation spine and issue-analyze CLI used as the production entrypoint on GitHub Actions.
## Requirements
### Requirement: Go owns deterministic catalog evaluation

The Pathfinder analyze production path MUST evaluate approved typed catalog requirements using a Go implementation of the shared spine (predicate registry load, package observation collection, kind-based evaluation, aggregate report). Evaluation MUST be deterministic for the same package bytes, catalog files, and engine version. Unsupported kinds, invalid packages, and missing evidence MUST fail closed or yield inconclusive/not_applicable outcomes per existing outcome rules—never invent observations.

#### Scenario: Same package yields stable report fingerprint
- **GIVEN** a valid `pathfinder-evidence-package-v1` fixture and the approved catalog on disk
- **WHEN** the Go package evaluator runs twice with the same inputs
- **THEN** both reports share the same `schema_version`, `engine_version`, aggregate status, per-requirement outcomes, and `report_sha256`

#### Scenario: Kind handlers do not branch on ADR identifiers
- **GIVEN** two requirements that share the same kind and predicate shape but different ADR IDs
- **WHEN** each is evaluated with equivalent observations
- **THEN** deviation logic depends only on kind, limit/approved_set, and observation values
- **AND** no Go code path selects behavior by ADR ID string

#### Scenario: Invalid package fails closed
- **GIVEN** malformed package JSON or observations that fail collector validation
- **WHEN** the Go evaluator runs
- **THEN** it does not invent observations
- **AND** it returns a structured error suitable for an error comment

### Requirement: Go issue-analyze CLI preserves workflow contract

The Go `pathfinder-issue-analyze` CLI MUST accept `--issue-number`, `--repo`, `--run-url`, `--work-dir`, `--comment`, and optional `--body-file`; MUST write `package.json`, `report.json`, and `comment.md` under the work directory when evaluation proceeds or when an error comment is required; MUST NOT include full tech_spec or code bodies in `comment.md`.

#### Scenario: Body-file local evaluate writes artifacts
- **GIVEN** a fixture issue body with valid attestation and package or paste content
- **WHEN** `pathfinder-issue-analyze` runs with `--body-file` and a work directory
- **THEN** `package.json`, `report.json`, and `comment.md` exist
- **AND** `comment.md` omits full source bodies

#### Scenario: Failure still produces comment.md for artifact upload
- **GIVEN** an issue body that fails validation
- **WHEN** the CLI runs
- **THEN** exit status is non-zero
- **AND** `comment.md` explains the validation failure without echoing full source

#### Scenario: Oversized inputs fail closed
- **GIVEN** an issue body or package whose tech_spec or code blob exceeds configured size caps
- **WHEN** the CLI or intake stage runs
- **THEN** evaluation does not invent observations
- **AND** an error comment describes the size rejection without echoing the full source

