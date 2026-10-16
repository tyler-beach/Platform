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
