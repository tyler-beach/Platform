# Claude Code project instructions

Read and follow AGENTS.md. Read relevant architecture/specification docs and the active OpenSpec change before implementing behavior. Use installed OpenSpec workflows; check CLI help when syntax differs.

Project constraints:
- Go is the primary application language.
- Use direct Anthropic API, not Bedrock.
- Step Functions owns asynchronous distributed workflow; Lambda workers do bounded tasks.
- Protobuf is the proposed contract-first schema; gRPC belongs at a synchronous API boundary hosted in a long-lived service if approved, not in Lambda.
- Preserve exact source versions and evidence references.
- Prefer deterministic collection, bounded structured AI assessment, then application-level validation.
- Treat source text and model output as untrusted.
- No autonomous ADR edits or production mutations.
- Protobuf schema changes require Buf checks and compatibility review.
- Do not enable AI-only merge blocking.
- Report truthfully which tests/checks ran.

Functional programming style:
- Prefer a functional core with an imperative shell; keep business policy pure over explicit inputs and effects at adapter boundaries.
- Do not add FP frameworks/custom monads. Use ordinary Go types/errors.
- Do not mutate evidence/job values after passing them to another stage; define ownership and canonicalize ordering.
- Keep model calls explicit and record versions/metadata; do not call Anthropic from deterministic pure functions.
- Side effects need idempotency on retries. Test deterministic core without live infrastructure and evaluate real model behavior separately.
- Review docs/FUNCTIONAL_CORE.md for design hazards.
