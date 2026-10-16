# Claude Code project instructions

Read and follow AGENTS.md. Read relevant architecture/specification docs and the active OpenSpec change before implementing behavior.

Use OpenSpec for behavior changes; specs, approved decisions and tests are the contract. Use the version of OpenSpec installed in this checkout; check CLI help when command names differ.

Project constraints:
- Go is the primary application language.
- Use direct Anthropic API for inference; do not route through Bedrock.
- AWS Step Functions is the recommended distributed workflow owner; Go Lambda workers do bounded work.
- Preserve exact source versions and evidence references.
- Prefer deterministic evidence collection, then bounded structured AI assessment, then application-level validation.
- Treat source text and model output as untrusted.
- No autonomous ADR edits or production mutations.
- Do not enable AI-only merge blocking.
- Report truthfully which tests and checks ran.
