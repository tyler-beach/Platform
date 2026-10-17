# Proposal: GitHub Actions audit workflow and ADR evaluation corpus

## Why

The PoC can collect YAML/JSON observations without a language selection, but the primary GitHub Actions workflow still requires a language and does not pass a configuration source. Observation envelopes and coverage reports are written to JSON artifacts, while the persistent CSV ledger omits them. This leaves config-focused analyses less reproducible and makes the audit trail incomplete.

The project also needs a broader, versioned corpus of natural-language ADRs that exercises availability, identity, authorization, encryption, resilience, data handling, and operational controls. The corpus must test intake and evidence collection without implying that mock-provider outcomes measure semantic model quality.

## What changes

- Allow the existing manual GitHub Actions analysis workflow to run with a language analyzer or with configuration sources alone.
- Persist observations and collection coverage in additive CSV tables, linked to the same run and artifact versions as findings and confidence scores.
- Record a source-collection stage in run events and preserve existing append-only CSV table headers for compatibility with the `poc-database` branch.
- Add 50 synthetic, natural-language ADRs and a versioned case manifest with domain, expected evidence capability, gold disposition, and pinned fixture expectation.
- Add an offline corpus audit that verifies every ADR and fixture is traceable, supported source facts are collected accurately, and unsupported/ambiguous cases remain inconclusive. Report mock semantic abstention separately from evidence extraction checks.
- Run the corpus audit in the existing GitHub Actions evaluation workflow.

## Scope and non-goals

This change improves the executable PoC and its GitHub Actions workflow. It does not deploy production infrastructure, implement runtime AWS/Kubernetes adapters, create an ADR-specific parser, introduce a policy DSL, or treat mock outputs as measured model quality. The corpus is synthetic test data, not independently adjudicated enterprise ground truth.

## Acceptance criteria

- A workflow-dispatch run can select `none` for language and collect a YAML/JSON configuration root without invoking language tooling.
- Each emitted observation and collection report is persisted to CSV with its run ID, exact source artifact hash/version, locator or coverage diagnostics, and redaction state.
- A prior CSV database containing only the existing table set can be loaded without changing or rejecting its existing headers.
- The pipeline event log includes source collection start/completion and accurately marks partial or failed collection.
- Exactly 50 unique natural-language ADR documents appear in the checked-in corpus, spanning the requested infrastructure, authentication, authorization and other architecture domains.
- The offline corpus audit checks all 50 manifest records, pins expected observation facts to fixture artifact hashes/locators, produces a report and machine-readable results, and does not report semantic model accuracy from the mock provider.
- Tests demonstrate the workflow/CLI behavior, CSV round trip and backwards-compatible table initialization, corpus integrity, and coverage-based inconclusive behavior.

## Risks and rollback

Additional CSV tables are additive and do not alter existing table schemas. If the new tables cannot be loaded or persisted, the workflow must fail visibly while retaining the run artifact. The corpus is synthetic and should not be used to set production thresholds. Revert the additive workflow inputs and tables if the ledger branch format or Actions experience proves incompatible.

## Decisions needing review

- Which observation fields are retained in persistent CSV versus linked JSON artifacts.
- Whether the initial 50-case gold labels are suitable for regression use; they require architecture review before quality thresholds are inferred.
