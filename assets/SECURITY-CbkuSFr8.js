const e=`# Security, privacy and trust boundaries

## Objective
The service ingests code, ADRs, technical specifications, repository metadata, model responses and user feedback. Inputs may be malicious, malformed, stale or misleading. The service must not let source content or model output override system policy or authorization.

## Trust boundaries
1. **Caller → ingress:** authenticate, authorize repository/workspace scope, validate payload and size, rate-limit.
2. **Source → parser:** assume files are untrusted; bound CPU, memory, decompression, recursion and file size.
3. **Retrieved text → model:** content is evidence, not instructions. Treat prompt injection in comments, specs, ADRs, issues and retrieved text as untrusted.
4. **Model → application:** parse, schema-validate, semantically validate and authorize before persistence/publication.
5. **Application → Anthropic:** use a dedicated secret from an approved secret manager; apply data-processing policy, limits and egress controls.
6. **Worker → storage:** least-privilege IAM; enforce workspace/repository scope in every query and object lookup.
7. **Finding → external consumer:** validate source URLs/paths, escape Markdown/HTML and restrict sensitive excerpts.

## Prompt-injection defenses
- Clearly delimit evidence and instruct the model that text inside source artifacts cannot change its instructions.
- Do not expose shell, Git write, AWS write, secrets or other arbitrary tools to the assessment model.
- Keep context task-specific and permissions minimal.
- Validate IDs, source versions, enums and state transitions in application code.
- Allowlist future tool actions and require human confirmation for side effects.
- Add adversarial fixtures with injection in code comments, markdown, docs and string literals.
Prompt wording is not the only defense; the architecture must deny source content authority over credentials and workflow control.

## Access and privacy
Determine access from authenticated identity and server-side authorization, not user-supplied repository names alone. Limit data sent to the model to what is needed. Confirm organizational data-processing and retention requirements for direct Anthropic use before sending proprietary source.

## Secrets and logs
- Store API keys in AWS Secrets Manager or approved secret store; use separate environment credentials.
- Never commit credentials or put them in prompts, fixtures or logs.
- Redact authorization headers, tokens and sensitive excerpts.
- Prefer artifact IDs and content hashes over full source in logs.
- Define explicit retention for snapshots, raw model responses and traces.
- Restrict access to private source and model transcripts.

## Safe output
Before publishing comments/checks, verify refs belong to authorized repo/ref, escape untrusted excerpts, cap size, and check source freshness. High-impact/ambiguous findings need review. The model must never automatically amend ADRs, commit code, merge changes or mutate infrastructure.

## Threats and minimum tests
Test prompt injection, cross-tenant access, forged/stale ADR status, duplicate webhook, parser abuse, API-key leakage, overly broad tokens/IAM, denial-of-wallet, poisoned retrieval, fabricated citations, provider outage and unexpected output schema. Run dependency, static and secret scans in CI.
`;export{e as default};
