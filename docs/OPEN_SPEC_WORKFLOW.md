# OpenSpec workflow, guardrails and coding-agent tooling

## Purpose
OpenSpec makes behavior changes explicit before implementation. Specs describe intended behavior; change artifacts describe proposed deltas. It complements Git history and tests.

## Initialize / refresh
Install the current OpenSpec CLI and use its current syntax. From the repo root, the typical setup is:

~~~sh
openspec init --tools claude
openspec update
openspec list
openspec validate --all
~~~

Review generated integration files before committing. Official references: https://openspec.dev/docs/setup and https://openspec.dev/docs/cli. Commands/skills depend on the installed version/profile.

## Standard change loop
1. Explore existing code, specs, decisions and unknowns.
2. Propose one bounded change with goals/non-goals, acceptance criteria and risks.
3. Specify observable behavior with concrete success/failure/security scenarios.
4. Write design.md for cross-cutting, security, data-model, dependency or migration changes.
5. Break work into small verifiable tasks.
6. Human review proposal/spec/design/tasks before implementation.
7. Apply tasks while preserving agreed scope.
8. Verify implementation against requirements, tests and evaluations.
9. Archive only after verification and syncing current-state specs to behavior that shipped.

## Guardrails
- One change is one cohesive outcome, not a platform rewrite.
- Do not silently rewrite requirements to match implementation.
- Distinguish normative requirements from preferences.
- Every requirement needs at least one Scenario and observable behavior.
- AI requirements define evidence, uncertainty, validation and prohibited side effects.
- Every external call defines timeouts, retries/error classification and observability.
- Async processing defines idempotency, duplicate delivery, terminal states and retry exhaustion.
- Persisted entities define identity, lifecycle, provenance, retention and migration expectations.
- Tenant/permission/secret/source access/model-data changes require explicit threat analysis.
- New dependencies/services/runtimes must have a requirement and trade-off.
- For Protobuf changes, define compatibility expectations and run Buf lint/build/breaking checks. Never reuse removed field numbers/names.
- Keep the distinction between gRPC request/response and Step Functions async orchestration explicit. Do not add gRPC servers inside Lambda workers.
- Model output is untrusted and must be validated in application code.
- Do not mark tests/checks complete if they did not run.
- Keep diffs reviewable; state changed files, checks, risks, and uncertainty honestly.
- Do not introduce memory products, graph databases, LangGraph or multi-agent loops without demonstrated need.

## Validation
~~~sh
openspec validate --all
buf lint
buf build
buf breaking --against '.git#branch=main'
~~~

Run commands applicable to the change. Strict OpenSpec validation can be used when supported. Structural validation does not replace code tests, security checks, generated-code verification or AI evaluation.

## Archive / merge gates
Confirm acceptance scenarios pass; relevant tests/evaluations and schema checks ran; specs match shipped behavior; API/schema/workflow contracts remain compatible or are migrated; provenance/security/audit are preserved; operational docs are updated; no secrets or private source data were committed.

## Tool integrations
Use OpenSpec CLI to create/refresh Claude Code skills/commands. Generated tooling files are not the source of truth. Root AGENTS.md and CLAUDE.md provide agent guardrails; openspec/config.yaml provides artifact-specific guidance.
