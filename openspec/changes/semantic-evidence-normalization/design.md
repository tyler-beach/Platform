# Design: Semantic normalization into shared evidence

## Pipeline

1. Intake pins every artifact by content digest and source revision. The package identifies artifact kind and evidence role (`design_assertion` for technical specifications and design documents; `implementation_fact` for code/configuration/runtime input).
2. Existing deterministic extraction runs as today to provide the default path and safe fallback. When the repository explicitly opts in, a semantic adapter builds one canonical prompt from the pinned artifacts and a compact allowlist derived from the current predicate registry/catalog.
3. A token-count request measures the actual model request shape. If the count is unavailable or exceeds policy, no generation call is made. The generation call is single-attempt, deadline-bound, and capped at the configured output tokens.
4. The model may return only candidate `(artifact_id, predicate, subject, value, exact_quote)` records. It cannot choose the evidence role, revision, path, offsets, IDs, applicability, requirement outcome, or severity.
5. Go validates predicates, subjects, value types, output count, artifact membership and quote resolution. A quote must occur exactly once in the cited artifact; Go derives the locator, source hash, revision, role and evidence ID. Ambiguous or fabricated quotes are rejected and counted as unresolved.
6. Deterministic collectors validate the resulting common evidence objects. The generic engine evaluates each in-scope requirement independently for each role present in the input. Results carry `evidence_role`; proposed design alignment is not represented as implementation alignment.
7. The report records extraction mode, prompt/schema/model versions, counted and observed usage, budget decision, and safe provider request ID. It never stores or logs raw prompts/responses or credentials.

## Evidence envelope

Extend the existing observation shape additively:

- `evidence_role`: `design_assertion` or `implementation_fact`;
- existing `predicate`, `subject`, typed `value`, `evidence_id`, `artifact_id`, `revision`, `path`, `source_sha256` and typed `locator`;
- `collector` and `extractor_version` identify whether a deterministic or semantic adapter produced it.

Legacy caller-supplied observations without a role are normalized to `implementation_fact`. Artifact-derived observations always use the artifact's role. Model output does not contain a role.

## Allowlist and normalization

The semantic prompt receives only predicates supported by the current catalog registry, each with value type, concise description, compatible requirement kinds, and allowed catalog subjects. The schema constrains predicate/subject enumerations where supported; Go repeats all validation. Unknown concepts are not converted to ad-hoc predicates. Return their source span as unresolved where possible and leave matching catalog requirements inconclusive.

This establishes an input-format-neutral boundary, not a universal ontology. The current prototype loads the checked-in catalog and scopes the predicate allowlist by package domain; very large enterprise catalogs still need retrieval/partitioning so each semantic request receives only a bounded relevant subset. A new ADR using a supported predicate requires catalog data only. A new evidence capability still needs a shared collector or predicate definition, not a new end-to-end ADR flow.

## Role-aware evaluation

The requirement engine remains generic. The package evaluator partitions normalized observations by evidence role and invokes the same engine for each role expected by the pinned package. A spec-only package yields design results; code-only yields implementation results; mixed input yields both sets independently. Missing extraction in an expected role yields inconclusive for that role. Existing result rows gain a role field; aggregate status is computed across role-specific rows and the report exposes counts by role so users can distinguish proposal from implementation.

## Anthropic adapter and budget

- Direct Anthropic Messages API; model ID is configured, not hard-coded. Use structured tool output with a fixed schema and forced tool choice.
- `PATHFINDER_ENABLE_MODEL_EXTRACT` is an explicit opt-in. Missing API key/model when enabled is a classified configuration error.
- Token-count preflight uses the same system prompt, message content, tool schema and tool choice as generation. Default maximums are 20,000 input tokens, 4,000 output tokens, and 64 candidate facts; configuration may lower but not raise these ceilings in this prototype.
- At most one token-count request and one generation request per workflow invocation. No automatic retry/repair/verification call. The full preflight-plus-generation sequence has a 60-second deadline. Cancellation and API errors return typed failures.
- The model is configured with no tools other than the schema-only output tool. The workflow does not grant additional GitHub permissions to the model adapter.
- Detect likely credential literals before sending; when detected, skip semantic transmission and record that semantic extraction was skipped. Existing issue attestation remains required. Scanner coverage is best-effort and is not a guarantee that arbitrary secrets are identified.
- Source artifacts are explicitly framed as untrusted data. They cannot instruct the model to alter policy or reveal secrets.

## Alternatives considered

### Keep regex extraction only

Zero model cost and deterministic, but arbitrary spec wording remains mostly invisible. Retain as the opt-out/fallback path.

### Ask the model to produce findings directly

Fewer application steps, but would mix interpretation, evidence selection and compliance judgment; source links and role separation become harder to validate. Rejected. The model emits candidate evidence only.

### One model call per artifact or requirement

Can improve isolation but multiplies spend and creates divergent paths. Rejected for the prototype. One bounded call processes the submitted package and emits a shared set of evidence objects.

## Failure and security behavior

- If token counting fails or exceeds the cap, do not call Messages; deterministic fallback may still run and the report identifies semantic extraction as unavailable.
- If the model call fails, output is malformed, exceeds count/value caps, references an unknown artifact, or cannot be uniquely anchored, discard invalid candidates; never infer a compliant value.
- If semantic normalization is enabled but unavailable, preserve deterministic observations and mark the extraction method/failure category. Do not claim semantic coverage.
- Report excerpts are source-derived; model free-text rationale is not accepted as evidence.
- Rate limits and concurrency remain GitHub operational controls. The one-call cap bounds per-run provider usage, not aggregate organization spend across unlimited runs.

## Verification

- Unit tests: role inference, exact quote-to-source location, duplicate/ambiguous quote rejection, predicate/subject allowlist, type/range checks, deterministic IDs, budget boundaries and fallback semantics.
- HTTP adapter tests with a local fake server: token preflight, exact request shape, auth header redaction, provider error classification, deadline, one generation attempt, usage capture and malformed responses.
- End-to-end package tests: semantically phrased spec + Go/Python code produce same predicate/subject with separate roles; evaluator emits separate outcomes; unsupported and absent claims stay inconclusive.
- Adversarial fixtures: prompt injection, invented evidence IDs, wrong artifact, forged quote, secret-like content, invalid enum/value, conflicting facts and output flooding.
- Labeled extraction fixtures record expected evidence spans and expected abstentions. Live model evaluation is not required for ordinary Go tests; report as not run unless credentials and a controlled eval are explicitly available.
