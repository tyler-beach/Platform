# Functional analysis demo

<span class="page-eyebrow">GITHUB ACTIONS / WALKTHROUGH</span>

Use the [Functional Analysis Demo workflow](https://github.com/tyler-beach/Platform/actions/workflows/functional-analysis-demo.yml) to run a synthetic analysis from input selection through source parsing, evidence packaging, budget preflight, a mock model response, evidence validation and a final report.

The workflow is designed to make the boundaries and artifacts visible in GitHub Actions. All inputs are synthetic. The mock-model stage makes no network requests and uses no secrets.

## Run it

1. Open the [workflow page](https://github.com/tyler-beach/Platform/actions/workflows/functional-analysis-demo.yml) in the repository.
2. Select **Run workflow**.
3. Choose a comparison and sample case, then start the run.
4. Open each job in the workflow graph to inspect its logs and step summary.
5. Open the final job summary, then download the `functional-analysis-demo` artifact to inspect every intermediate JSON file and the complete Markdown report.

## Select a comparison

| Comparison input | Inputs pinned for the run | Deterministic analysis |
|---|---|---|
| `code-diff` | Synthetic Go handler, its diff and ADR-001 | Parse the handler with `go/parser` / `go/ast`; extract selected call sites and diff evidence |
| `technical-spec` | Synthetic Markdown specification and ADR-001 | Extract requirement statements and classify explicit execution constraints; AST is not applicable |
| `spec-vs-implementation` | Async technical specification, synthetic Go handler and diff | Parse the handler and compare its call sites with the specification requirement |

## Select a sample case

| Sample case | Example behavior | Expected outcome |
|---|---|---|
| `deviation` | Direct provider call conflicts with the decision, or the specification explicitly requires synchronous execution | `supported_deviation` |
| `aligned` | The handler enqueues work, or the specification requires the asynchronous workflow | `no_deviation_found` |
| `insufficient-evidence` | A helper call hides the actual behavior, or the specification does not say whether work is synchronous | `inconclusive` |

The expected outcome is stored in a separate test-oracle file. The mock-model stage does not read that oracle. The final validator compares the candidate with the oracle to make sure every workflow option exercises the intended path.

## Workflow graph

~~~mermaid
flowchart TD
  A["1 · Admit + pin inputs"] --> B["2 · AST + document analysis"]
  B --> C["3 · Evidence contract"]
  C --> D["4 · Budget preflight"]
  D --> E["5 · Mock LLM assessment"]
  E --> F["6 · Validate citations + outcome"]
  F --> G["7 · Report + downloadable evidence bundle"]
~~~

## What each stage emits

| Stage | Main artifact | Purpose |
|---|---|---|
| Admission | `input-manifest.json` | Records the selected mode, fixture origin, byte length and SHA-256 source version |
| AST / document analysis | `ast-analysis.json`, `analysis.json` | Records parsed call sites, extracted requirements and the analysis limits |
| Evidence contract | `evidence-package.json`, `evidence-contract-check.json` | Assigns stable evidence IDs and ties every excerpt to a source artifact, version and locator |
| Budget gate | `budget-decision.json` | Shows an estimated input size, output reservation and call ceiling for the demo |
| Mock model | `mock-model-response.json` | Shows the structured candidate response, prompt/model fixture versions, rationale and evidence IDs |
| Validation | `validation-result.json` | Checks that citations exist, versions match, required support types are present and the outcome matches the fixture expectation |
| Final report | `functional-analysis-report.md`, `functional-analysis-report.json` | Summarizes the run and is included with all intermediate artifacts |

## Evidence record shape

An evidence item follows this illustrative contract:

~~~json
{
  "evidence_id": "EV-AST-001",
  "artifact_id": "ART-CODE-001",
  "artifact_version": "sha256:<digest of exact input bytes>",
  "source_path": "run-data/input/handler.go",
  "locator": {
    "kind": "source-line",
    "line_start": 4,
    "line_end": 4
  },
  "evidence_type": "ast_call_site",
  "fact": "synchronous_provider_call: direct call observed at this site",
  "excerpt": "h.anthropic.Assess"
}
~~~

The actual line number and digest depend on the selected sample. The validator checks every cited ID against the exact evidence package and checks that evidence versions correspond to the input manifest.

## What the mock model does—and doesn't

The mock model is a deterministic fixture ruleset shaped like a structured model response. It returns an outcome, rationale, limitations, evidence IDs and run metadata. It does not call Anthropic, estimate actual provider billing, claim production AST coverage, or prove transitive runtime behavior. The budget uses a small character-based estimate only to demonstrate the preflight stage and reservation fields.

A successful run means that the demo pipeline, evidence contract and fixture expectation agree. It is not an accuracy evaluation of a language model or an implementation of the production analysis service.
