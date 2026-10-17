# Functional analysis demo

> For the current end-to-end ADR PoC workflow, generated evidence/confidence outputs, and recent GitHub Actions runs, open the [interactive PoC demo](demo/index.md).

<span class="page-eyebrow">GITHUB ACTIONS / WALKTHROUGH</span>

Run the [Functional Analysis Demo workflow](https://github.com/tyler-beach/Platform/actions/workflows/functional-analysis-demo.yml) to follow a synthetic analysis from input selection through parsing, evidence assembly, budget preflight, a mock assessment, validation and a final report.

## Run a scenario

1. Open the [workflow](https://github.com/tyler-beach/Platform/actions/workflows/functional-analysis-demo.yml) and select **Run workflow**.
2. Pick the comparison, source language and sample outcome.
3. Start the run. Open each job in the graph to see its log and step summary.
4. Open the final job summary and download the `functional-analysis-demo` artifact for the full set of intermediate files and the Markdown report.

## Choose the comparison

| Comparison | Inputs | Work performed |
|---|---|---|
| `code-diff` | A synthetic source file, its diff and ADR-001 | Parse the changed implementation, extract syntax-node observations, inspect added diff lines and compare evidence with the ADR. |
| `technical-spec` | A synthetic Markdown specification and ADR-001 | Extract requirement statements, classify explicit execution constraints and compare them with the ADR. Code parsing is skipped. |
| `spec-vs-implementation` | A synthetic technical spec, source file and diff | Parse the source and compare its call-site observations with the requirement. |

## Choose a source language

The code path uses [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) through the pinned `tree-sitter-language-pack` package. Each grammar feeds the same output and evidence contract.

| Trigger option | Fixture extension |
|---|---|
| `go` | `.go` |
| `python` | `.py` |
| `javascript` | `.js` |
| `typescript` | `.ts` |
| `java` | `.java` |

Tree-sitter gives us real language parsing and exact syntax-node source spans. The current call labels are deliberately simple receiver/method heuristics; they are not type resolution or proof of transitive runtime behavior. The technical-spec-only path uses the deterministic Markdown extractor instead.

## Choose the outcome to exercise

| Sample | What the fixture contains | Expected result |
|---|---|---|
| `deviation` | A direct provider-shaped call, or a requirement that explicitly calls for synchronous execution | `supported_deviation` |
| `aligned` | An enqueue/workflow handoff, or a requirement for asynchronous processing | `no_deviation_found` |
| `insufficient-evidence` | A helper call hides its behavior, or the spec leaves execution mode unspecified | `inconclusive` |

The expected result lives in a separate test-oracle file. The mock-model step cannot read it. The final validator compares the candidate outcome with that oracle after checking the evidence package.

## The workflow

~~~mermaid
flowchart TD
  A["1 · Admit + pin inputs"] --> B["2 · Tree-sitter + document analysis"]
  B --> C["3 · Evidence contract"]
  C --> D["4 · Budget preflight"]
  D --> E["5 · Mock assessment"]
  E --> F["6 · Validate citations + outcome"]
  F --> G["7 · Report + downloadable evidence bundle"]
~~~

The jobs intentionally pass versioned artifacts between stages. You can open a stage, inspect its output, and then follow the corresponding JSON file in the downloaded run bundle.

## Stage outputs

| Stage | Output | What to inspect |
|---|---|---|
| Admission | `input-manifest.json` | Selected mode/language, fixture origin, file size and SHA-256 version |
| Parsing and extraction | `ast-analysis.json`, `analysis.json` | Grammar, parse status, call target, enclosing function, source span, selected diff lines and requirements |
| Evidence | `evidence-package.json`, `evidence-contract-check.json` | Evidence IDs bound to artifact IDs, source hashes, locators, facts and excerpts |
| Budget gate | `budget-decision.json` | Input-size estimate, output reservation and call ceiling |
| Mock assessment | `mock-model-response.json` | Structured candidate, rationale, limitations, evidence IDs and model/prompt fixture versions |
| Validation | `validation-result.json` | Source hashes, exact syntax-node spans, evidence references, support types and expected outcome |
| Final report | `functional-analysis-report.md`, `functional-analysis-report.json` | Run summary, cited evidence and validation results |

## Evidence item shape

A Tree-sitter call-site evidence record includes a source locator down to the exact byte range of the syntax node:

~~~json
{
  "evidence_id": "EV-TS-001",
  "artifact_id": "ART-CODE-001",
  "artifact_version": "sha256:<digest of exact input bytes>",
  "source_path": "input/handler.py",
  "locator": {
    "kind": "tree-sitter-node",
    "line_start": 3,
    "line_end": 3,
    "start_byte": 74,
    "end_byte": 113
  },
  "evidence_type": "syntax_call_site",
  "fact": "synchronous_provider_call: direct call observed at this site",
  "excerpt": "self.anthropic.assess(ctx, request)"
}
~~~

The actual span depends on the selected language and fixture. Validation slices the pinned source bytes using the recorded offsets and requires an exact match to the excerpt. It also verifies that the artifact ID and SHA-256 version resolve to the current run's input manifest.

## What the mock does

The mock assessment is a deterministic ruleset that emits the shape expected from a model response: outcome, rationale, limitations, evidence IDs and run metadata. It makes no network requests and uses no secrets. The budget is a character-based demonstration estimate, not a provider tokenizer, reservation service or billing calculation.

A green run means that parsing, evidence construction, reference validation and the selected fixture expectation agree. It does not measure LLM accuracy or prove behavior beyond the code and evidence included in the scenario.
