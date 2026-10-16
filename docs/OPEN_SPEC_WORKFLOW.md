# OpenSpec workflow, guardrails and coding-agent tooling

## Purpose
OpenSpec makes behavior changes explicit before implementation. Its specs describe intended behavior; change artifacts describe proposed deltas. It complements Git history and tests.

## Initialize / refresh
Install the current official OpenSpec CLI. From the repo root, run:
~~~sh
openspec init --tools claude
openspec update
openspec list
openspec validate --all
~~~
Review any generated integration files before committing. OpenSpec installs both a local openspec structure and tool-specific skills/commands. Names and syntax depend on installed version/profile; check the installed CLI and official guides at https://openspec.dev/docs/setup and https://openspec.dev/docs/cli.

## Standard change loop
1. Explore code, current specs, decisions and unknowns.
2. Propose one bounded change with problem, goals/non-goals, acceptance criteria and risks.
3. Specify observable behavior with concrete scenarios, including failures and security boundaries.
4. Write design.md for cross-cutting change, new dependencies, data-model changes, significant security/performance concerns or migration.
5. Break work into testable tasks.
6. Human review proposal/spec/design/tasks before code.
7. Apply tasks while preserving approved scope.
8. Verify implementation against requirements and tests.
9. Archive only after checks and spec sync; specs must reflect behavior that actually shipped.

## Guardrails
- One change = one cohesive outcome, not an entire platform rewrite.
- Don't silently rewrite the spec to fit existing code.
- Distinguish normative requirements from preferences.
- Every requirement needs at least one Scenario and measurable observable behavior.
- AI behavior requirements define evidence references, uncertainty, output validation and prohibited side effects.
- Every external call defines timeout, retry/error policy and observability.
- Every asynchronous job defines idempotency, duplicate delivery, terminal state and retry exhaustion.
- Every entity defines identity, lifecycle, provenance, retention and migration expectations.
- Changes involving tenant scope, permissions, secrets, source access or model data processing need threat analysis and explicit review.
- Justify each new dependency/service/runtime and describe operational/exit costs.
- Never mark tasks complete when checks did not run.
- State skipped checks honestly.
- Keep changes small enough for human review; summarize files, tests, security implications, risks and unresolved questions.
- Do not introduce LangGraph, memory products, a graph DB or multi-agent loops without an evidenced requirement.

## Validation and CI
~~~sh
openspec validate --all
openspec validate --all --strict
~~~
Strict mode is useful when supported by the installed version. Structural validation is not proof of semantic correctness, test coverage or security. Run code tests, static/security checks and AI evaluation separately.

## Archive / merge checklist
Confirm acceptance scenarios pass; applicable tests and evals run; specs match shipped behavior; contracts and migrations are safe; provenance/audit/security remain intact; operational docs are updated; no secrets or private samples were committed.

## Tool files
Use the CLI to create/refresh Claude Code skills/commands. Treat generated tool files as tooling integration, not the source of truth. Root AGENTS.md and CLAUDE.md provide cross-tool project guardrails; openspec/config.yaml provides artifact/operation-specific guidance.
