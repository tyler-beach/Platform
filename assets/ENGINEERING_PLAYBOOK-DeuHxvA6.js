const e=`# Engineering playbook: OpenSpec + functional + behavioral + test-driven development

OpenSpec is the behavior contract, not a substitute for code review or tests. The required pattern is specification-first, test-first, then implementation and evidence-based verification.

![OpenSpec-first delivery cycle.](assets/diagrams/engineering-loop.svg)

## The change lifecycle

### 1. Explore before proposing

Read README, architecture/contract docs, current state specs, active OpenSpec changes, decisions, code and tests. Verify which capabilities exist. Classify the change as docs-only, refactor, or behavior change. Never infer implementation from a target diagram.

Create one bounded change directly under openspec/changes. Record observable outcome, non-goals, affected comparison modes/contracts, risk, migration/rollback, decisions needing approval and acceptance criteria.

### 2. Write behavior before implementation

Requirements describe externally observable behavior. Use normative words only where intent is clear. Every requirement needs concrete Given/When/Then scenarios. Include normal behavior and relevant failures: unauthorized access, stale source, repeated delivery, timeout, cancellation, partial evidence, budget exhaustion and adversarial content. Missing evidence is not proof of compliance.

Maintain traceability from requirement to scenario to test:

| Requirement / scenario | Test proof | Test level | Release condition |
|---|---|---|---|
| Stable applicability from same snapshot | Same result for same inputs/policy | Unit/property | Every PR |
| Repeated create request | Same key/request reuses job; changed request conflicts | API + DB integration | Every PR |
| Ambiguous workflow start | Reconciler repairs without duplicate logical work | Fault-injection integration | Before pilot |
| Fabricated/stale evidence | Candidate rejected or inconclusive; no publication | Unit + security | Every PR |
| Prompt/model update | Labeled before/after results reviewed | AI eval | Before model rollout |
| Budget exceeded | Call blocked or deterministic compaction applied | Unit + harness integration | Every PR |

Test names should include capability/requirement/scenario identifiers where practical so reviewers can go from spec to the exact behavioral proof.

### 3. Test-first loop

1. Add scenario fixtures and a test for the expected observable outcome.
2. Run the new test and confirm it fails for the expected reason (RED).
3. Implement the smallest coherent pure-domain change or adapter effect (GREEN).
4. Refactor without changing the contract.
5. Run focused tests then the applicable broader gates. Record actual command output honestly.

A docs-only change can use a narrow exception. A behavior, API/schema, retrieval, prompt, token policy, state-machine or security change is not “docs-only” because implementation does not yet exist; it needs an OpenSpec change and planned/actual test evidence.

## Layer the tests

| Layer | What belongs here | External services? |
|---|---|---|
| Unit/table-driven | Outcomes, state transitions, evidence rules, budget arithmetic, canonicalization, validators | No |
| Property/fuzz | Hash stability, parser bounds, canonical order, line mapping and invariants | No |
| Contract | Protobuf compatibility, API/OpenAPI mapping, errors/enums, persistence and event schema | No live cloud required |
| Adapter integration | DB constraints/transactions, source adapters, Anthropic request mapping, Step Functions contract | Fakes/local dependencies or controlled test account |
| Resilience/fault injection | Duplicate delivery, crash, lost response, dispatch gap, timeout, throttling, cancellation race, partial fan-out | Controlled test environment |
| Labeled AI evaluation | Precision/recall, applicability, evidence support, abstention, retrieval quality and drift | Provider calls are separate from unit suite |
| Adversarial/security | Prompt injection, cross-tenant IDs, forged refs, secret leakage, parser abuse, Markdown injection, denial-of-wallet | Safe fixtures/isolated environment |
| End-to-end/shadow | Representative path from ingress through result and review | Dedicated sandbox |

Keep deterministic tests repeatable. LLM evaluations pin source artifacts, expected outcomes and acceptable evidence spans. Score semantic outcomes and invariants rather than exact prose.

## Functional core / imperative shell

Put deterministic transformations in ordinary Go packages with explicit inputs and returned values. Keep AWS, DB, provider, filesystem, clock/ID generation, telemetry and publication at adapter/use-case boundaries.

- Use typed structs/enums; unspecified zero values must not accidentally mean no deviation.
- Don't mutate source/stage values after handoff. Define slice/map ownership and copy at transfer boundaries where needed.
- Canonically sort before hashing, prompting or stable-order assertions.
- Use idiomatic errors and errors.Is/errors.As; don't create custom monad/effect frameworks.
- Keep domain outcomes (supported, potential, no deviation found, inconclusive) distinct from technical failures.
- Treat model response as an immutable candidate artifact and validate it before effectful persistence.

## OpenSpec commands and gates

Use the installed CLI and check its help if syntax differs. Typical commands:

~~~sh
openspec list
openspec status <change-name>
openspec validate <change-name>
openspec validate --all
~~~

Before implementation, review proposal + delta specs + design + tasks. Before archive, run acceptance scenarios and applicable tests/evaluations, reconcile specs with what shipped, then use the installed CLI's supported archive command. Never archive just to clear the active-change list.

For Proto changes, run Buf lint/build/breaking checks. For docs changes, run the React Pages/OpenAPI build. Once implementation and tests exist, CI should enforce unit, contract, security and relevant AI-evaluation gates. This playbook does not mean those future application gates are already configured.

## Pull request checklist

- [ ] Reviewed OpenSpec change exists for behavior change.
- [ ] Requirements have observable scenarios and tasks identify test proof.
- [ ] Regression test failed for the expected reason before fix where practical.
- [ ] Pure core remains deterministic over explicit versioned inputs.
- [ ] Side effects have deadlines, bounded retries and idempotency.
- [ ] Auth, tenant, evidence and redaction paths have adversarial coverage.
- [ ] Token/cost/call/deadline budgets are tested for model changes.
- [ ] Unit/contract/integration and applicable AI evals ran; skips are disclosed.
- [ ] Schemas/docs are aligned and compatibility/migration is clear.
- [ ] Operational limits, metrics, alerts and replay/rollback are described.
- [ ] Active change is archived only after acceptance and spec sync.
`;export{e as default};
