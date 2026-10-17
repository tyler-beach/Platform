# OpenSpec workflow, guardrails and coding-agent practice

## Purpose

OpenSpec captures the intended behavior delta before implementation, while tests provide the evidence that the behavior actually exists. Specs are not implementation proof, and passing structural validation does not replace automated tests, security review or AI evaluation.

The complete practice is in the [engineering playbook](ENGINEERING_PLAYBOOK.md); the [adversarial design review](ADVERSARIAL_DESIGN_REVIEW.md) lists the major failure modes and proposed contract controls.

## Initialize and inspect

Install/use the current OpenSpec CLI version and check its help because CLI syntax can evolve. Typical commands:

~~~sh
openspec init --tools claude
openspec update
openspec list
openspec status <change-name>
openspec validate <change-name>
openspec validate --all
~~~

Review generated instruction files before committing. Official references: [OpenSpec CLI](https://openspec.dev/docs/cli) and [spec-driven schema](https://openspec.dev/docs/schemas/spec-driven).

## Standard change loop

1. Explore current code, tests, OpenSpec specs, active changes, contracts, decisions and open questions.
2. Create one bounded proposal with outcome, scope, non-goals, risks, migration/rollback and decisions needing human approval.
3. Write observable behavior scenarios for success and relevant failure/security paths; preserve normative language and uncertainty.
4. For cross-cutting changes, write design alternatives and operational failure behavior.
5. Break work into checkbox tasks that identify the test or other acceptance proof.
6. Review proposal/spec/design/tasks before implementation.
7. Write a failing behavioral/regression test first where practical; confirm RED for the expected reason.
8. Implement the smallest pure-domain slice and explicit side effects; keep diffs reviewable.
9. Run focused tests plus applicable broader contract, integration, security, resilience and AI-evaluation gates; record real outputs.
10. Reconcile the current-state specs with shipped behavior. Archive only when acceptance criteria and required checks are satisfied.

## Required scenario coverage

Include relevant cases for: duplicate request/event; same idempotency key with different request; stale source and evidence locator; cross-tenant access; permission denial; malformed/unsupported input; partial branch failure; retry exhaustion; deadline/cancellation race; budget exhaustion; provider timeout after possible acceptance; prompt injection; fabricated or wrong-version evidence; publication freshness and duplicate side effects.

## Functional-core guardrails

- Deterministic policy/evidence transformations are pure functions over explicit snapshots/policy versions where practical.
- DB/network/time/random/workflow/model/filesystem effects live behind adapters/use cases.
- Stage outputs have defined ownership; no mutation of handed-off evidence; canonical sort where order affects prompt, hash or evaluation.
- Domain outcomes are separate from technical errors.
- Use normal Go types, constructors/validators and errors; no bespoke monad/effect system.
- Idempotency and constraints protect effects. Purity doesn't make a remote call exactly-once.

## Validation matrix

| Change type | Required evidence |
|---|---|
| Pure domain rule | Unit/table-driven + property tests where useful |
| Parser/normalizer/retrieval | Unit/fuzz + golden evidence mapping and retrieval benchmark where relevant |
| Protobuf/API/DB schema | Buf/OpenAPI checks, compatibility/migration tests, authorization tests |
| Workflow/effect changes | Duplicate/replay, injected crash, retry/deadline, cancellation and partial-failure tests |
| Prompt/model/retrieval/finding semantics | Labeled before/after AI eval, evidence validity, cost/latency, human review |
| Security/data policy | Threat update, adversarial fixtures, redaction/tenant tests |
| Docs-only | React Pages/OpenAPI build and link/content review |

For Protobuf changes, use Buf lint/build/breaking checks. For documentation, run the React Pages/OpenAPI build. Application test/evaluation gates must be introduced with the implementation rather than claimed to exist today.

## Archive gate

Do not archive a change just to clear it from the active list. Confirm the acceptance scenarios and relevant tests ran; required skipped checks have an explicit reviewed exception; source/evidence provenance is preserved; contracts and migration strategy are aligned; and docs reflect behavior that shipped. Record untested or deferred items truthfully.
