## ADDED Requirements

### Requirement: Validate ADR markdown structure offline

The ADR pack import tool MUST validate a directory of markdown ADRs without calling a model or network API. Validation MUST report structural errors and readiness gaps that block a Pathfinder pack build.

#### Scenario: Missing Decision section fails
- **GIVEN** a markdown ADR file without a `## Decision` section (or equivalent Decision heading)
- **WHEN** `validate` runs
- **THEN** the tool reports an error for that file
- **AND** the overall validate exit status is non-zero when any error exists

#### Scenario: Missing domain warns
- **GIVEN** an ADR with a Decision section but no Domain metadata
- **WHEN** `validate` runs
- **THEN** the tool reports a warning for missing domain
- **AND** does not invent a domain value

### Requirement: Scaffold typed sidecars without approving them

The tool MUST scaffold a typed requirement sidecar for each ADR that lacks one. Scaffolded sidecars MUST be marked as needing human typing and MUST NOT be approved for pack inclusion.

#### Scenario: New ADR gets a draft sidecar
- **GIVEN** an ADR markdown file with no sidecar
- **WHEN** `scaffold` runs
- **THEN** a `.md.req.json` sidecar is written
- **AND** `label_status` is `needs_human_typing`
- **AND** `approval_state` is not `approved`

#### Scenario: Completed sidecar is not overwritten by default
- **GIVEN** a sidecar with `approval_state=approved` and required fields filled
- **WHEN** `scaffold` runs without a force flag
- **THEN** the sidecar file content is left unchanged

### Requirement: Build pack only from completed approved sidecars

The tool MUST build Pathfinder catalog artifacts only from sidecars that are complete and approved. Incomplete or draft sidecars MUST be excluded or cause a fail-closed build when strict mode is enabled.

#### Scenario: Draft sidecar excluded from build
- **GIVEN** a sidecar still marked `needs_human_typing`
- **WHEN** `build` runs in default mode
- **THEN** that ADR is not written into `requirements.jsonl`
- **AND** the build report lists it as skipped pending review

#### Scenario: Approved complete sidecar is packaged
- **GIVEN** an approved sidecar with kind, predicate, subject, domain, decision, and applicability
- **AND** the ADR markdown digest is available
- **WHEN** `build` runs
- **THEN** a requirements row is emitted with `adr_revision` bound to the markdown SHA-256
- **AND** the predicate is present in the emitted `predicates.json`

### Requirement: Heuristics never auto-approve

Deterministic text heuristics MAY suggest kind, limit, or predicate candidates. Suggestions MUST be labeled and MUST NOT set `approval_state` to `approved`.

#### Scenario: Numeric MUST NOT exceed suggests numeric_max
- **GIVEN** a Decision section containing `MUST NOT exceed 600`
- **WHEN** scaffold heuristics run
- **THEN** the sidecar may include a suggested `kind` of `numeric_max` and `limit` of `600`
- **AND** `approval_state` remains not approved
- **AND** a `suggestion_source` of `heuristic` is recorded

### Requirement: Optional Claude suggestions are budgeted and never approving

The tool MAY offer an opt-in Claude suggestion command for incomplete sidecars. Default operation MUST remain offline. Live calls MUST require explicit execute confirmation, enforce call/token budgets, prefer cache hits, send Decision text (not full unbounded ADR bodies), and MUST NOT set `approval_state` to `approved`.

#### Scenario: Dry-run does not call the model
- **GIVEN** incomplete draft sidecars
- **WHEN** `suggest` runs without execute confirmation
- **THEN** no Anthropic Messages request is sent
- **AND** the report counts how many ADRs would be eligible within budget

#### Scenario: Execute fills drafts but does not approve
- **GIVEN** an incomplete sidecar and Claude Code CLI auth
- **WHEN** `suggest --execute --yes` runs within budget
- **THEN** empty kind/predicate/subject fields may be filled from model JSON
- **AND** `approval_state` remains `draft`
- **AND** model metadata (provider, model id, prompt hash, token usage, request id) is recorded on the sidecar

#### Scenario: Suggest does not require Anthropic API key
- **GIVEN** `claude` is installed and logged in locally
- **AND** `ANTHROPIC_API_KEY` is unset
- **WHEN** `suggest --execute --yes` runs
- **THEN** the tool invokes the Claude Code CLI print mode
- **AND** it does not open an in-process Anthropic HTTPS client

#### Scenario: Budget stops further calls
- **GIVEN** more incomplete ADRs than `--max-calls`
- **WHEN** suggest execute runs
- **THEN** at most `--max-calls` Messages requests are made
- **AND** remaining ADRs are reported as skipped for budget
