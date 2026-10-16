# Adversarial design review: functional programming in Go

**Status:** Recommended engineering constraints for implementation; review before treating them as normative project policy.

## Verdict

Use a **functional core, imperative shell** architecture. Keep domain decisions and evidence transformations deterministic, mostly pure Go functions; isolate I/O, clocks, randomness, model calls, databases, AWS APIs and publication at explicit boundaries. This is practical functional programming in Go—not an attempt to imitate Haskell with deeply nested generic abstractions.

The current design already has useful ingredients: typed artifacts, evidence-first analysis, immutable source versions, explicit workflow states, and deterministic verification. The risks are that these principles remain prose rather than package/API constraints, and distributed retries and model behavior can undermine referential transparency if not designed intentionally.

## Functional core, imperative shell

~~~mermaid
flowchart LR
  subgraph Shell["Imperative shell (effects)"]
    IN["RPC / event ingress"]
    ORCH["Step Functions / adapters"]
    STORE["Repositories, clock, IDs"]
    MODEL["Anthropic API"]
    OUT["Persistence / publish"]
  end
  subgraph Core["Functional core (pure transformations)"]
    NORM["Normalize input value"]
    RULES["Applicability + deterministic rules"]
    EVIDENCE["Build evidence package"]
    RESULT["Validate / classify candidate"]
  end
  IN --> ORCH
  ORCH --> STORE
  STORE --> NORM
  NORM --> RULES
  RULES --> EVIDENCE
  EVIDENCE --> MODEL
  MODEL --> RESULT
  RESULT --> OUT
~~~

The shell retrieves data and performs effects. It passes plain values to the core. The core returns values and explicit errors; it does not query databases, call Anthropic, read the current clock, mutate global state or publish findings.

## High-value functional principles

### 1. Make transformations pure where possible
Examples: normalize ADR metadata; classify a job transition; resolve applicability from supplied decision metadata and relationships; rank/trim supplied evidence under a budget; validate candidate finding references against a supplied evidence package; compute a stable finding fingerprint from explicit input fields.

Given the same explicit inputs and policy version, these functions should return the same outputs and errors. If a function needs current time, DB state, randomness or a model response, make that dependency explicit or keep it in the shell.

### 2. Treat source and stage outputs as immutable values
Go does not enforce deep immutability. Treat structs crossing stages as values that are not mutated after publication. Avoid shared mutable pointers, maps and slices. Copy slices/maps when ownership changes; document ownership on APIs; use immutable IDs/hashes for large content rather than cloning huge source blobs gratuitously.

Don't use one globally mutated job object that every stage silently edits. Prefer small stage input/output types with explicit version and evidence references.

### 3. Use sum-type-like modeling with Go structs and enums
Go has no native sum types. Use tagged structs/enums and constructor/validation functions; make invalid states difficult to construct. Model SupportedDeviation, PotentialDeviation, NoDeviationFound and Inconclusive as distinct outcomes or a tagged outcome with outcome-specific validation. Avoid ambiguous booleans or a zero-valued enum interpreted as "no deviation."

Every enum's zero value should be unspecified/invalid unless a deliberate safe default is documented. Validate Protobuf transport types before mapping them to domain types.

### 4. Make effects explicit at the edges
Use narrow ports/interfaces for external effects: artifact repository, decision repository, model assessor, job store, workflow starter, clock, ID generator and publisher, but only at real boundaries. A use case can orchestrate those interfaces; a pure domain function should not need them.

Prefer ResolveApplicability(input) over a function that secretly reads the database, clock and environment variables.

### 5. Model failure as data at stage boundaries
Use typed error categories for invalid input, not found, unauthorized, stale source, retryable provider outage, rate limit, deadline, invalid model response, evidence incomplete and internal failure. Keep error handling idiomatic Go with error wrapping and errors.Is/errors.As rather than a custom Result monad framework.

A normal domain result such as Inconclusive is not necessarily a technical error. Keep domain outcomes distinct from execution failures.

### 6. Keep commands and queries distinct
Queries return data without observable mutation. Commands describe changes and carry idempotency identity. CreateAnalysisJob has database/workflow effects; GetAnalysisJob should not. Avoid getters that also create or modify state.

### 7. Make nondeterminism explicit
Model calls are nondeterministic effects. Pass the exact evidence package, prompt/schema versions, model configuration, budget and job ID into the harness. Capture response metadata and persist the result. Do not hide live LLM calls inside a function advertised as pure or inside a deterministic unit test.

Pure pre-processing and post-validation should be reproducible, with model output treated as an input artifact to downstream checks.

### 8. Deterministic ordering and canonicalization
Go map iteration order is unspecified. Sort IDs, candidate lists, evidence references, output findings and serialized collections whenever ordering influences prompts, fingerprints, cache keys or evaluation results. Canonicalize line endings and normalized representations carefully. Stable prompt input improves reproducibility, caching and eval comparability.

### 9. Pure policy, effectful execution
Separate policy from execution:
- pure transition decision: NextState(current, event, policy);
- effectful adapter: persist state and start/cancel the remote workflow;
- pure rule: EvaluateConstraint(evidence, decision);
- effectful AI task: ModelAssessor.Assess(ctx, request);
- pure verifier: ValidateFinding(candidate, evidence, policy).

Do not spread authoritative policy across Lambda handlers, prompts, Step Functions expressions and database triggers.

### 10. Retry-safe side effects
Pure functions are naturally retryable, but DB inserts, workflow starts and GitHub comments can duplicate. Use idempotency keys and unique constraints; persist intent/status before launching side effects; make publication idempotent. Don't assume a timeout or cancellation undoes an external action.

## Adversarial findings against the current design

| Risk | Why it undermines functional design | Required guardrail |
|---|---|---|
| Shared mutable AnalysisJob passed to all stages | Hidden coupling/order dependence | Stage-specific input/output values; persisted versioned state |
| Repository queries inside domain predicates | Same input can yield different decisions | Load a snapshot; pass relevant facts explicitly |
| Clock/random IDs buried in core logic | Non-reproducible tests | Inject clock/ID at shell or pass values explicitly |
| LLM call hidden inside an "analysis" function | Purity boundary concealed | Separate ModelAssessor effect and persist request/result metadata |
| Map/slice mutation after stage handoff | Races and corruption | Ownership rules, copies at ownership transfer, no mutation after handoff |
| Nondeterministic evidence order | Prompt/eval/fingerprint drift | Canonical sort and deterministic truncation |
| Retry duplicates job/finding/comment | Side effects are not exactly-once | Idempotency keys, unique constraints, outbox/reconciliation where needed |
| Ambiguous zero enum or success/error booleans | Invalid states leak downstream | Constructors/validators, explicit outcomes and typed failures |
| Error-string inspection | Fragile retry/control flow | Typed/sentinel errors and explicit retryability classification |
| Prompt is the only policy enforcement | Source can influence conclusions | Enforce authorization, evidence validity and allowed transitions in Go |
| Step Functions, API and agent graph all own state | Conflicting authorities | One top-level lifecycle owner; graph, if any, is a bounded sub-workflow |
| Prompt/model aliases mutate without run metadata | Results cannot be compared | Store effective model/prompt/schema configuration per run |
| Confidence presented as calibrated probability | False precision | Separate model score from calibrated metrics/evidence quality |
| In-place reindex changes history | Findings point to changed content | Version derived indexes against immutable source versions |
| Telemetry stores arbitrary prompts/output | Data leaks via observability | Metadata-first tracing; restricted/redacted payload capture only |

## Recommended Go shape

~~~go
// Pure function: all facts and policy are explicit. No I/O or model calls.
func ValidateEvidenceRefs(candidate CandidateFinding, evidence EvidencePackage, policy ValidationPolicy) ValidationResult {
    // Return a new result; do not mutate candidate or evidence.
    // Real implementation should reject missing and wrong-version references.
}

// Effectful boundary: owns API calls and external failure semantics.
type ModelAssessor interface {
    Assess(ctx context.Context, req AssessmentRequest) (AssessmentResult, error)
}
~~~

This is an illustrative interface, not compilable standalone code; concrete types and imports must exist in implementation.

## Functional programming should not become dogma

Do not build custom monads/effect systems in Go to avoid ordinary error returns; clone megabytes of source content at every stage; make every struct an interface; pretend network/model effects are pure; replace database transactions/unique constraints with transformations; or require identical model output across calls. The goal is a deterministic, composable domain core with visible effects and safe replay—not purity at any cost.
