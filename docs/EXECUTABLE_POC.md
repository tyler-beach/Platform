# Executable PoC: Semantic Analysis, Evidence, and Audit

This is the executable proof of concept for the ADR Deviation Platform. Launch Actions → ADR Deviation PoC Analysis → Run workflow. The default is the Go fixture and deterministic mock provider, so it requires no model key and makes no model API call.

The [interactive PoC demo](demo/index.md) shows a generated fixture run through each stage, displays source-version evidence and confidence components, and browses GitHub Actions job status. Detailed CSV-backed run records are included only when a private-repository build verifies private Pages access and the explicit `PAGES_REAL_RUN_DATA_ENABLED=true` repository variable. Pull-request builds never receive the ledger token.

## What runs for real

1. **Admit and pin inputs.** The run captures source/spec/ADR/diff inputs, file sizes, SHA-256 hashes, and a run ID.
2. **Parse syntax.** Tree-sitter parses the selected source tree and stores source file inventory, syntax errors, node counts, and hashes.
3. **Resolve symbols and calls.** Language-specific tooling builds definitions and direct call edges. Go uses go/packages, go/types, SSA and CHA. TypeScript/JavaScript uses the official TypeScript compiler API. Java uses the JDK compiler model. Python indexes AST scopes/imports plus explicit type hints and obvious constructor assignments.
4. **Build transitive reachability.** Select an entry function (the default is Submit). The runner follows resolved edges and marks every edge reachable from that entry. Unresolved calls stay visible, but are not silently treated as resolved edges.
5. **Create evidence.** Normative requirements, reachable call edges, and diff lines become evidence objects with IDs, paths, line numbers, artifact hashes, and excerpts.
6. **Budget and assess.** The workflow performs a token-budget gate. Mock mode uses a deterministic assessment adapter. Anthropic mode uses the Messages API, a required structured tool schema, a configurable model name, and the prompt in .poc/prompts/assess.md.
7. **Validate and persist.** The application checks the outcome schema and verifies every cited evidence ID belongs to this run. It writes a Markdown report, JSON bundles and linked CSV rows.

The same manual GitHub Actions workflow also supports a configuration-only run: select `none` for language and supply a YAML/JSON `config_source`. The `source_path` can be the same directory. No language resolver is invoked in that mode. Code files still require a selected language.

## Run against a repository path

The workflow's source_path must point to a directory inside the checked-out repository. Set the matching language, root_function, ADR path, and technical-spec path. A diff can be supplied through diff_path; otherwise the workflow uses source_path/change.diff when it exists, or can generate a Git diff from the optional base/head refs.

The fixture includes an intentional sync call path through Handler.Submit, Worker.Execute, and AnthropicClient.Assess; the accompanying spec requires asynchronous/non-blocking provider assessment. It exercises interprocedural evidence instead of a method-name-only regex.

## Confidence scoring and auditability

The report has two different confidence fields on purpose:

- **Model self-reported confidence** is retained for evaluation. It is not trusted as evidence, is not used in the score, and should not be interpreted as calibrated.
- **Evidence-strength score (0–100)** is computed deterministically by `.poc/confidence.py`. It is an explainable support rating—not a statistical probability until we calibrate it against labeled evaluation data.

The score is a weighted calculation with a versioned algorithm:

| Dimension | Weight | What it checks |
|---|---:|---|
| Requirement clarity | 20% | Whether a cited normative requirement states a specific, operational constraint |
| Observation resolution | 25% | Call paths are bounded by their least-certain edge; direct configuration facts use the collector resolution status |
| Requirement-observation linkage | 20% | Whether a validated explicit link names the requirement and observed source behavior and labels the relationship |
| Evidence coverage | 15% | Whether citations cover the requirement and observed behavior |
| Provenance integrity | 10% | Whether every citation resolves to a pinned input artifact and its excerpt hash matches |
| Analysis completeness | 10% | Whether the entry resolves, parsing/semantic diagnostics exist, and reachable dynamic edges remain |

The calculation stores the raw score for each dimension, its weight and contribution, the explanation, supporting evidence IDs, and any cap/guardrail. A score is capped at 49/100 when no normative requirement or resolved cited source observation exists, and at 39/100 when citation/provenance validation fails. A `supported_deviation` is downgraded if it lacks a cited normative requirement, a cited source observation, or a validated `contradicts` link connecting them; it is also downgraded if relevant collection coverage is incomplete, an observation is unresolved, or evidence integrity fails.

The evidence package is intended to answer **what, why, and how**: which requirement line conflicts, which changed/source line and edge support the observation, how the analyzer resolved that edge, which transitive path reaches it, which exact input artifact hash was analyzed, and which uncertainty reduced the score. Open `confidence.json` and `callgraph.json` beside `evidence.json` for the full machine-readable trail. CSV tables `confidence_assessments.csv` and `confidence_components.csv` preserve the score and its component arithmetic. `assessment_evidence_links.csv` records each requirement-to-observation link, including the relationship and explanation.

The weights and thresholds are initial PoC policy, not empirically calibrated truth. Before using this to enforce architecture policy, build a labeled evaluation set of true violations, non-violations, and ambiguous cases; measure precision/recall and calibration; tune thresholds; and retain a human review path for material findings.

## Semantic limits are explicit

- Go's CHA graph is conservative and may include multiple possible targets for interface calls. It is not a proof of the single target taken at runtime.
- TypeScript/JavaScript resolution depends on compiler options, source files, declaration files, and available typing/JSDoc. Interface calls add known in-repository implementers as possible targets.
- Java binding requires the source set and dependencies to be available. The JDK resolver labels unresolved bindings and external methods rather than inferring bodies.
- Python's dynamic dispatch, reflection, monkey-patching, and weakly typed receivers can defeat static resolution. This adapter resolves supported intra-project scopes/imports and obvious receiver types and emits unresolved edges for the rest.
- Tree-sitter is the shared syntax parser, not itself a type checker. Language-specific compiler/type information is what resolves call targets.
- The mock model does not call a provider and is not a substitute for evaluating model quality. Only the decision stage is mocked; its deterministic rules consume the same evidence contract as Anthropic mode.
- The budget gate uses Anthropic's token-count endpoint in real-provider mode before sending a Messages request; measured usage from the Messages response is also recorded. Mock mode uses a character-based token estimate.

## CSV audit database

The source tables live in .poc-db/. CSV files are one table each; CSV itself cannot contain multiple workbook tabs. Rows are append-only and linked by run_id, artifact_id, symbol_id, edge_id, evidence_id, and transaction_id.

| CSV table | Purpose |
|---|---|
| runs.csv | Run identity, comparison inputs, model/provider, outcome, and status |
| run_events.csv | Pipeline stages, statuses, timestamps, and structured detail |
| artifacts.csv | Input paths, size, and SHA-256 source versions |
| symbols.csv | Function/method index, signatures and resolver status |
| call_edges.csv | Direct call sites, target IDs, resolution basis, dispatch kind and reachability |
| evidence.csv | Normative requirement, code-edge, configuration and diff evidence with source spans |
| observations.csv | Versioned language-neutral observations joined to run, artifact, locator and evidence IDs |
| collection_reports.csv | Per-source completeness, unsupported/failed files, counts and sanitized diagnostics |
| budget_reservations.csv | Input/output budget, estimate, decision and measured usage |
| llm_transactions.csv | Provider, model, prompt hash, request ID, status, usage, duration and error |
| findings.csv | Validated assessment candidate and evidence references |

The GitHub workflow serializes writes and persists the tables on a separate poc-database branch, then uploads the current CSV snapshot and run bundle as an Actions artifact. This keeps generated audit rows out of the architecture/source branch. The branch is a reviewable PoC ledger, not a transactional multi-writer database. contents: write must be allowed for the workflow's GITHUB_TOKEN.

The additive observation and coverage tables do not change older CSV headers. Each source-collection stage writes start/completion events; partial collection is recorded as partial and prevents a supported-deviation outcome.

## Enable Anthropic

Add an Actions secret named ANTHROPIC_API_KEY. Select anthropic from the workflow's model provider control. Optionally set the repository variable ANTHROPIC_MODEL; otherwise it uses the default in .poc/model.py. The API key is read from the environment and is not written to CSV, JSON artifacts, or logs.

The prompt and output schema are version-controlled. The model is treated as an untrusted candidate: citations and the response shape are checked deterministically before a finding is accepted. No production deployment or merge-blocking action is implied by this PoC.
