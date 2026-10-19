# Proposal: Semantic normalization into shared evidence

## Why

The issue analysis path currently extracts a narrow set of observations with deterministic patterns and then evaluates those observations against the catalog. A new technical specification expressed in unfamiliar language usually produces no evidence, even when it describes a decision the catalog can evaluate. Code and specification input also lack an explicit evidence role, so the report cannot cleanly distinguish proposed design claims from implementation facts.

## What changes

- Add an opt-in, one-pass Anthropic semantic normalizer for a pinned issue package. It extracts bounded, structured evidence from both specification and implementation artifacts.
- Normalize both artifact types into the same validated observation contract. Record whether each observation is a design assertion or an implementation fact; derive that role from the pinned artifact metadata, never from model output.
- Restrict extraction to catalog-approved predicates, subjects and value types. Require an exact quote from the source and resolve its location locally; model-provided offsets and evidence IDs are never trusted.
- Evaluate evidence by role through the existing generic requirement engine. Keep proposed-design and implementation results separate while using the same requirement and outcome semantics.
- Bound provider use with a token-count preflight, a hard input/output token ceiling, one generation call per workflow run, a fixed deadline and no automatic generation retries. Keep semantic extraction disabled unless explicitly opted in and configured.
- Preserve the deterministic extractor as the default and fallback when semantic extraction is disabled or safely skipped. A provider/configuration/validation failure must be visible and must not silently turn into a semantic success.

## Scope and non-goals

In scope: GitHub Pathfinder issue analysis, Go domain/adapter code, the common evidence role/provenance contract, model budget controls, structured output validation, workflow configuration, and prototype evaluation fixtures.

Out of scope: Bedrock integration, ADR database/vector retrieval, arbitrary new predicate authoring, multi-call agent loops, semantic model decisions about compliance, production AST/data-flow analyzers, automatic policy enforcement, and changing the ADR corpus.

## Acceptance criteria

- A full pasted technical specification can produce source-grounded design-assertion evidence for predicates already supported by the catalog, even when its wording is not one of the existing regex patterns.
- Pasted code and same-repository PR files can produce source-grounded implementation-fact evidence in the same envelope.
- The same predicate/subject from a specification and code artifact is evaluated separately by evidence role; one role cannot overwrite or conflict-collapse the other.
- No model-generated ID, role, predicate outside the catalog allowlist, subject, value type, revision, path, line or span is accepted without application validation against the pinned package.
- Ambiguous, unsupported, conflicting, unlocatable, or incomplete extraction remains inconclusive; absence of model output is never interpreted as alignment.
- With semantic extraction disabled, there is no Anthropic network call and the current deterministic behavior remains available.
- With semantic extraction enabled, each workflow run makes at most one generation request, only after token-count preflight and secret-like-input screening; it never exceeds the configured hard input/output limits.
- Prompt injection in an artifact cannot change the schema, allowlist, workflow behavior, permissions, or provider budget.
- Provider usage/model/prompt/schema/version and budget disposition are included as bounded metadata without storing prompts, raw provider responses or credentials in logs.

## Risks and rollout

- Semantic normalization can still misinterpret a statement. Treat its output as candidate evidence, validate source citations and types, keep outcomes advisory, and add a labeled before/after evaluation set.
- Predicate/subject coverage remains bounded by the catalog. Unsupported claims are surfaced as unresolved/inconclusive instead of receiving a made-up predicate.
- The opt-in GitHub Actions secret transmits issue content to Anthropic. Keep the workflow disabled by default, retain the existing public/synthetic attestation, and require repository administrators to configure the provider secret and model variable explicitly.
- A single bounded call can still be repeated by users or workflow reruns. Repository-level Actions limits and concurrency remain operational controls; this change does not claim a cross-run dollar ledger.
- The deterministic extractor remains a fallback, not semantic analysis. The report must identify which method ran.

Rollback: unset the repository variable `PATHFINDER_ENABLE_MODEL_EXTRACT` or remove the Anthropic secret. This restores deterministic extraction without changing package consumers.

## Decisions requiring review

- Review the `design_assertion` and `implementation_fact` role names and the role-specific result presentation.
- Review the initial default ceilings (20,000 counted input tokens, 4,000 output tokens, one generation call, 60-second call deadline) before enabling the workflow in a private organization.
- Confirm whether existing manually supplied observations without a role should default to `implementation_fact` for backward compatibility.
