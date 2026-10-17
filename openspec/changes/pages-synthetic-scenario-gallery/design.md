# Design: Pages synthetic scenario gallery

## Current behavior

The docs workflow creates one `.poc/run.py` walkthrough and exports one evidence-focused snapshot. The Functional Analysis workflow supports three comparison modes and three sample outcomes, but Pages only links to that workflow; it cannot browse its input files. Workflow history is an independent bounded live API/static projection and can be disabled.

## Proposed data flow

During the docs build, a deterministic catalog builder runs the existing `.github/demo/pipeline.py` stages against each of the nine mode/sample pairs. It runs Tree-sitter only for code-bearing comparisons. Each run uses a temporary directory; the builder validates the final report, outcome, evidence, artifact paths, and SHA-256 digests before collecting a bounded allowlist of JSON stage summaries and UTF-8 input text.

On non-PR Pages builds, a separate read-only exporter queries the approved Functional Analysis workflow and examines at most ten successful default-branch `workflow_dispatch` attempts from the last 13 days. It verifies repository/workflow/run identity through the Actions API before artifact lookup, requires the exact artifact name and owning run, verifies the Actions artifact digest, and invokes the existing `project_bundle` validator before reading any bundle member. It additionally binds each input role/path to the comparison, case, and language path layout under `.github/demo/fixtures`; only those exact input bytes and bounded allowlisted output summaries are emitted. Expired or rejected artifacts are not rendered and their bounded counts are included in catalog status. The compact live-run projection is merged into the generated static catalog, preserving the nine curated scenarios if no live artifact qualifies.

The page loads that same-origin JSON independently of the current walkthrough and Actions history. The UI renders scenario selection buttons and an input grid. For spec-versus-implementation cases, technical specification and source are the first paired panes, with ADR and diff shown alongside/below. For other modes, only the artifacts actually admitted by that mode are shown. Live entries display the actual Actions run and attempt, workflow SHA and artifact digest. Evidence IDs are linked to artifact paths and line ranges. Stage statuses and validation checks are shown; fixture outcomes are explicitly identified as deterministic mock results, not AI quality or confidence.

The generator uses fixed comparison/sample enums and the known fixture directory layout. It resolves and validates every input under `.github/demo/fixtures`, enforces per-file and aggregate byte caps, rejects invalid UTF-8, and writes only after all nine scenarios validate. The browser validates the catalog schema/shape and inserts all untrusted strings through `textContent`/text nodes.

## Alternatives

- **Use only the existing Actions history panel:** rejected because run metadata and links do not expose a browsable, stable scenario matrix or source side-by-side view; retention and opt-in history also make it a poor demo baseline.
- **Download recent run artifacts in the browser:** rejected because artifacts are untrusted, time-limited, and would couple a public site to source-bearing workflow bundles and API access.
- **Generate one catalog directly from fixtures without running the pipeline:** rejected because it could show expected stories without proving that the actual deterministic workflow stages and validators produce them.

## Security, privacy, and failure handling

The repository and Pages site are public, so only synthetic source is allowed. The live importer is read-only, rejects pull-request and non-default-branch runs before artifact lookup, enforces a bounded run count/age/archive size, and validates artifact identity/digest plus source/evidence hashes before projection. It never runs or sources bundle content, preserves prompts or credentials, or accepts arbitrary fixture paths. The static fixture builder is constrained to the fixture root and rejects size overruns, hash mismatches, malformed outputs, or failed validation. Browser rendering uses text content, and no unvalidated artifact URL is dereferenced. Curated catalog generation failure fails the docs build; invalid live artifacts are skipped and counted while the curated gallery remains intact.

## Cost and performance

The build executes nine local mock runs and Tree-sitter parses, with no network calls from the analysis pipeline. The separate artifact exporter makes bounded authenticated GitHub API requests and downloads at most ten small artifacts; retries and requests have deadlines. Source fixtures and bounded summaries add a static JSON payload with an aggregate ceiling. Browser rendering loads one same-origin JSON file and only creates panes for the selected scenario.

## Migration and rollback

Add a versioned JSON file, generator, page section, styles, and browser-core tests. Preserve the existing sample walkthrough and history behavior. Rollback removes the generator invocation and gallery UI; no persistent data migration is needed.
