# Contributing

## Before behavior changes
1. Read README, relevant docs, accepted decisions and current OpenSpec specs.
2. Inspect existing code and tests; do not assume docs perfectly match code.
3. Create a focused OpenSpec change for behavior changes.
4. Resolve high-impact unknowns affecting schema, security, workflow ownership or user-visible semantics before implementation.
5. Define testable acceptance criteria.

## During implementation
- Follow Go conventions and keep AWS/provider code behind adapters.
- Prefer deterministic, testable logic.
- Preserve source versions and evidence provenance.
- Treat imported content and model output as untrusted.
- Test success, edge cases, authorization failures and retry/idempotency.
- Update tests/specs/docs together with behavior.
- Never commit secrets or proprietary sample artifacts.

## Before completion
- Run gofmt, go vet, tests, selected linter/security checks and OpenSpec validation as applicable.
- Run evaluation fixtures for changes to retrieval, prompts, schemas or finding semantics.
- Report exact checks run and any skipped checks.
- Review the diff for secret/source-data exposure.
- Confirm every published finding resolves to the exact source version.
- Update OpenSpec plans when scope changes rather than checking tasks simply because code exists.

## Change summary
Explain motivation, behavior, trade-offs, migrations, security implications, tests/evaluations, observability, risks and unresolved questions. AI-generated code is tested and reviewed like any other code.
