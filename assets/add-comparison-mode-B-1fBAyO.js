const e=`# How to add a comparison mode

A comparison mode defines what is compared and what evidence is needed, not merely another enum value.

## Required design work

1. State the question answered and supported input types.
2. Define input cardinality, immutable-version requirements, and missing/unsupported input behavior.
3. Define applicable decision/requirement retrieval and when applicability remains unknown.
4. Define deterministic checks, expected evidence types, locator precision and counter-evidence behavior.
5. Define meanings of supported deviation, potential deviation, no deviation found and inconclusive.
6. Add labeled positive, negative, ambiguous, irrelevant-decision and adversarial fixtures before tuning prompts.
7. Version extraction, policy, prompt, output schema and finding fingerprints.
8. Update Protobuf/OpenAPI, validators, contract tests and docs together if public API changes.
9. Measure evidence validity, quality, latency, cost and inconclusive rate.

## Acceptance criteria

- No final claim references an unprovided evidence ID.
- An ADR does not become binding solely through semantic similarity.
- Missing/stale evidence yields inconclusive or a documented review outcome.
- Equal immutable inputs and policy produce stable deterministic pre-model output.
- Quality is evaluated against a reviewed corpus before enforcement is enabled.
`;export{e as default};
