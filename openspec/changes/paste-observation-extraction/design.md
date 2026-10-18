## Goals

- Paste markdown and/or Go/Python → sparse typed observations → catalog evaluation with some confident outcomes.
- Deterministic, local, no model calls in the extractor (models must not manufacture evidence).
- Public-repo safe comments unchanged.

## Non-goals

- Full coverage of all 100 predicates from arbitrary prose.
- Treating “not mentioned” as `false` for presence/required predicates.
- Automatic secret redaction of issue bodies (attestation + docs remain the control).

## Flow

1. Package has tech_spec/code content and empty/missing observations
2. Language/path heuristics select markdown, Python AST, and/or Go literal scanners
3. Allowlisted rules emit observations with catalog subjects + span locators
4. Conflicts on `(predicate, subject)` drop all candidates for that key
5. `package_collector` validates as `structured_package`
6. Engine evaluates; gaps stay `inconclusive`

## Allowlist policy

Start with predicates that have explicit numeric/boolean/string grounding in text or AST/literals (TTL, idle timeout, encryption, TLS policy tokens, replicas, probes, retries/DLQ, rate limit, MFA claims, secrets-in-source=true only, sensitive log=true only, structured logging signals, password min length, etc.). Expand only with tests.

## Conflict / silence

- Two different values → emit neither.
- No match → emit nothing (not `false`).
- `security.secret_in_source.present` and similar forbidden-presence predicates emit `true` only.
