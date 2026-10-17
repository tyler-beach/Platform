# Executable ADR Deviation PoC

This directory contains an executable vertical slice, not just a visual demo. It performs real source parsing, language-aware symbol/call resolution, transitive reachability, evidence hashing, budget preflight, structured model response validation, and CSV audit writes. Only the model decision itself is simulated when MODEL_PROVIDER=mock.

## Run locally

    python -m pip install -r .poc/requirements.txt
    python .poc/run.py --language go --source .poc/fixtures/go --root-function Submit --comparison spec-vs-implementation --provider mock --run-id local-001

## Run the labeled evaluation set

    python .poc/evaluation/evaluate.py --provider mock --output-dir /tmp/adr-evaluation

## Simulate ADR scope retrieval and flag candidates

    python .poc/scope/run_scope.py --output-dir /tmp/adr-scope-report

This runs the offline ADR catalog, filters by lifecycle/repository/service/domain/language, ranks candidates, and emits review-only cue flags with source hashes. To run one change event use `--event-json /path/to/change-event.json`. The opt-in Bedrock/Aurora adapter is documented in docs/ADR_SCOPE_RETRIEVAL.md; CI never calls AWS.

The labeled evaluation suite runs 14 synthetic boundary cases, records outcome metrics and a review-gate threshold sweep, and emits both Markdown and JSON reports. Labels are provisional until architecture reviewers independently adjudicate them. The evidence-strength score is not a probability. See docs/EVALUATION.md for scope, metrics, limits, and how to opt into live-model evaluation.

For TypeScript/JavaScript, Node.js 20+ and the pinned TypeScript compiler are required. For Go, Go 1.24+ is required. For Java, JDK 21+ is required. Python uses the standard-library AST and scope/index resolver, in addition to shared Tree-sitter syntax diagnostics.

## Enable Anthropic

Set MODEL_PROVIDER=anthropic, ANTHROPIC_API_KEY, and optionally ANTHROPIC_MODEL. The default model is configurable (currently claude-sonnet-5-5); no key is needed in mock mode. The Anthropic adapter uses the Messages API and a required tool schema to request a structured assessment. It records request metadata and token usage, never the API key or full authorization headers. The prompts live in prompts/assess.md.

In GitHub Actions, add ANTHROPIC_API_KEY as a repository or environment secret to activate the optional provider. Keep mock mode as the default until outbound provider calls are explicitly enabled.

## Semantic-analysis guarantees

Tree-sitter supplies common syntax parsing and exact source spans. Resolution is language-specific:
- Go uses go/packages, SSA, and a CHA call graph from golang.org/x/tools. CHA is a conservative over-approximation for dynamic/interface dispatch, not proof of the single runtime target.
- TypeScript and JavaScript use the official TypeScript compiler API/type checker. JavaScript resolution depends on available JSDoc/types and compiler settings.
- Java uses the JDK compiler model (Trees/Elements) against the source set and supplied classpath.
- Python indexes modules, scopes, imports, class methods, and obvious constructor/annotation bindings. Runtime monkey-patching, dynamic import, reflection, and unresolved Any/duck-typed calls remain explicitly unresolved.

Every edge carries a resolution status and basis; unresolved calls are retained as observations rather than silently discarded. The graph is transitive from the selected root function. It is an analysis of the supplied checkout/source tree; it does not execute the application.

## CSV database

.poc-db/ is the human-auditable database directory. Each table is one append-only CSV file, with a stable header and IDs linking records across tables. CSV itself has no worksheets, so each CSV corresponds to one table/sheet when opened or imported into a workbook. Workflow runs also upload the complete bundle as a GitHub Actions artifact and persist table updates to the dedicated poc-database branch. Source payloads are not copied into the database; hashes, paths, spans, evidence excerpts and transaction metadata are recorded.

Tables: runs, run_events, artifacts, symbols, call_edges, evidence, budget_reservations, llm_transactions, findings, confidence_assessments, confidence_components, and assessment_evidence_links.

## Limits

This is a single-runner PoC. The CSV branch is serialized with a GitHub Actions concurrency group; it is not a substitute for a transactional database under parallel production load. Model output is an untrusted candidate: the application validates its schema and evidence references before storing a finding. The mock provider produces a deterministic candidate and makes no network request.
