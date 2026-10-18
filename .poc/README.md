# Executable ADR Deviation PoC

This directory contains an executable vertical slice, not just a visual demo. It performs source parsing, language-aware symbol/call resolution, transitive reachability, evidence hashing, budget preflight, structured model response validation, and audit writes. Only the model decision itself is simulated when MODEL_PROVIDER=mock.

## Run locally

    python -m pip install -r .poc/requirements.txt
    python .poc/run.py --language go --source .poc/fixtures/go --root-function Submit --comparison spec-vs-implementation --provider mock --run-id local-001

## Replay one evidence-backed change

    python .poc/replay/replay_event.py --event-json .poc/scope/event-template.json --output /tmp/pathfinder-replay.json --verify-repeat

Replay uses the offline lexical ADR retriever and versioned cue rules. The report records event/catalog hashes, configuration, exact evidence IDs and excerpt hashes, matched ADRs, and a deterministic report fingerprint. Summaries alone are not accepted as evidence. A deviation is a review candidate; uncertain is a valid result when the evidence is insufficient. No model, AWS service, or live repository is queried by this replay command.

## Locked holdout quarantine

    python .poc/evaluation/audit_locked_holdout.py

The holdout seed set is separate from the 20-case development regression corpus and is fingerprint-locked. It is intentionally unlabeled and marked pending independent adjudication. CI checks the exact file hash, case IDs, evidence presence, and absence of gold labels. Do not use the cases to tune prompts, thresholds, retrieval, or rules. This is not yet an independent accuracy benchmark; only an approved, separately controlled adjudication/evaluation process may add labels and authorize scoring.

## End-to-end review feedback validation

After a review batch has been sampled, GitHub Issues have been created for selected units, and reviewers/adjudicators have appended valid events to the local hash-chained ledger, validate the cycle and export candidates:

    python .poc/review_sampling/validate_feedback_cycle.py --ledger /path/to/review-events.jsonl --sample-batch /path/to/review-batch.json --output-dir /tmp/pathfinder-feedback-cycle

The validator verifies every ledger event belongs to the recorded probability or risk sample, requires a prior disposition and a distinct adjudicator, validates the event hash chain, and exports only eligible candidate records. The audit records the baseline corpus hash before and after; the command never edits the development corpus or holdout. GitHub Issues remain intake, not the authoritative ledger, and a candidate export is not automatic promotion.

The probability sample and risk-triage queue remain separate; risk-only units have no population inclusion probability and must not be mixed into weighted quality estimates.

## Run the labeled development evaluation

    python -m unittest discover -s .poc/tests -v
    python .poc/evaluation/evaluate.py --provider mock --output-dir /tmp/pathfinder-eval
    python .poc/evaluation/evaluate_adr_corpus.py --output-dir /tmp/pathfinder-corpus

The 20 labeled cases currently exercise one narrow async-boundary domain and are synthetic, not independently adjudicated. The separate 50-ADR audit validates deterministic evidence collection, not semantic interpretation quality. Green CI proves only that the checks actually run pass; it is not a production-accuracy claim.

For TypeScript/JavaScript, Node.js 20+ and the pinned TypeScript compiler are required. For Go, Go 1.24+ is required. For Java, JDK 21+ is required. Python uses the standard-library AST and scope/index resolver, in addition to shared Tree-sitter syntax diagnostics.

## Enable Anthropic

Set MODEL_PROVIDER=anthropic, ANTHROPIC_API_KEY, and optionally ANTHROPIC_MODEL. The default model is configurable; no key is needed in mock mode. Live calls can be billable. The adapter records request metadata and token usage, never the API key or full authorization headers. Keep mock mode as the default until outbound provider calls are explicitly enabled.

## Semantic-analysis guarantees

Tree-sitter supplies common syntax parsing and exact source spans. Resolution is language-specific:
- Go uses go/packages, SSA, and a CHA call graph from golang.org/x/tools. CHA is a conservative over-approximation for dynamic/interface dispatch, not proof of the single runtime target.
- TypeScript and JavaScript use the official TypeScript compiler API/type checker. JavaScript resolution depends on available JSDoc/types and compiler settings.
- Java uses the JDK compiler model (Trees/Elements) against the source set and supplied classpath.
- Python indexes modules, scopes, imports, class methods, and obvious constructor/annotation bindings. Runtime monkey-patching, dynamic import, reflection, and unresolved Any/duck-typed calls remain explicitly unresolved.

Every edge carries a resolution status and basis; unresolved calls are retained as observations rather than silently discarded. The graph is an analysis of the supplied checkout/source tree; it does not execute the application.

## CSV database

.poc-db/ is the human-auditable database directory. Each table is one append-only CSV file, with stable headers and IDs linking records across tables. Workflow runs upload the complete bundle as a GitHub Actions artifact and persist table updates to the dedicated poc-database branch. Source payloads are not copied into the database; hashes, paths, spans, evidence excerpts and transaction metadata are recorded.

Tables include runs, run_events, artifacts, symbols, call_edges, evidence, budget reservations, and analysis outputs.
