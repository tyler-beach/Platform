# Claude Code project instructions

Read and follow AGENTS.md. Read relevant architecture/contracts and the active OpenSpec change before implementing behavior. Use the installed OpenSpec CLI and check help when syntax differs. See docs/ENGINEERING_PLAYBOOK.md and docs/ADVERSARIAL_DESIGN_REVIEW.md.

## Project constraints
- Go is the primary application language.
- Use direct Anthropic API, not Bedrock.
- Step Functions owns asynchronous distributed workflow; Lambda workers do bounded tasks.
- Protobuf is the proposed contract-first schema; gRPC belongs at a synchronous API boundary hosted in a long-lived service if approved, not in Lambda.
- Preserve exact source versions and evidence references.
- Prefer deterministic evidence before a bounded structured assessment and application validation.
- Treat source text and model output as untrusted.
- No autonomous ADR edits or production mutations.
- Protobuf schema changes require Buf checks and compatibility review.
- Do not enable AI-only merge blocking.
- A database commit and workflow start are not atomic; design durable dispatch and reconciliation.
- Model token/spend/call/time budgets span retries, repair and verification.
- Report truthfully which tests/checks ran.

## OpenSpec and development practice
- For behavior changes, prepare a bounded proposal, delta specs with observable Given/When/Then scenarios, design and checkbox tasks before implementation.
- Link requirements to tests/acceptance evidence. Add a failing regression test first where practical; implement the smallest slice; run focused and relevant broader tests.
- Run AI evaluations for changes to prompts, models, retrieval, parsers, schemas or finding policy.
- Archive only after behavior is verified and the current-state specs reflect shipped behavior.

## Functional programming style
- Prefer functional core / imperative shell; pure business policy over explicit versioned values and effects at adapter boundaries.
- Do not add FP frameworks/custom monads. Use ordinary Go types/errors.
- Do not mutate evidence/job values after stage handoff; define ownership and canonicalize ordering.
- Keep model calls explicit and record versions/usage. Do not call Anthropic from deterministic pure functions.
- Every external side effect needs deadline, retry classification, idempotency and telemetry.
- Never log secrets, full source or prompts by default.
- Review docs/FUNCTIONAL_CORE.md for adversarial checklist.
