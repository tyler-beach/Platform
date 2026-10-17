## ADDED Requirements

### Requirement: Functional Analysis audit persistence is explicit and replay-safe
Each persisted Functional Analysis record MUST bind the repository, workflow ID, workflow run ID and attempt, execution state, analysis state, optional domain outcome, pinned input artifact hashes, evidence references, validation summary, and persistence state. Those states MUST remain distinct. Persistence MUST be idempotent for the same run attempt and MUST distinguish duplicate delivery from a new attempt. Workflow-oracle agreement MUST NOT be represented as confidence. Confidence MUST be computed only from validated inputs accepted by a versioned confidence algorithm; otherwise it MUST be unavailable with an explicit reason. The writer MUST detect and reconcile eligible workflow attempts missing from the ledger; a concurrency queue alone MUST NOT be treated as durable delivery.

Only successful Functional Analysis runs from the repository default branch may produce a validated analysis record. Pull-request and non-default-branch runs MUST remain run-scoped and MUST NOT be ingested into the shared CSV ledger. A privileged writer MUST run trusted code from the default branch, use least-privilege Actions read and contents write permissions, and treat every downloaded artifact as untrusted data. Before artifact lookup/download, it MUST validate the source repository, workflow ID, event type, and default-branch name through the Actions API. It MUST validate run identity, attempt, artifact bounds and paths, schema, hashes, and evidence references before mutation. Existing CSV table headers MUST remain compatible through an additive versioned record table.

#### Scenario: A validated synthetic run is persisted
- **GIVEN** a completed Functional Analysis run from an approved source and a validated, versioned artifact bundle
- **WHEN** the ledger writer accepts the run
- **THEN** the record binds to the repository, run ID, attempt, input hashes, evidence references, execution state, and domain outcome
- **AND** the confidence field is either produced from the versioned evidence-strength algorithm's validated inputs or marked unavailable with a reason
- **AND** the fixture-oracle result is not described as confidence or model quality.

#### Scenario: The same run attempt is delivered twice
- **GIVEN** a ledger record already exists for the same repository, workflow run ID, and attempt
- **WHEN** the same run artifact is delivered again
- **THEN** the writer recognizes the existing logical record and does not append a duplicate
- **AND** any immutable-content mismatch is rejected and reported.

#### Scenario: A retry creates a new run attempt
- **GIVEN** a completed run attempt 1 and a rerun attempt 2 for the same Actions run ID
- **WHEN** both attempts are persisted
- **THEN** each attempt remains separately addressable
- **AND** consumers do not mistake the later attempt for a rewrite of the earlier audit record.

#### Scenario: An untrusted or invalid artifact is presented
- **GIVEN** an artifact with an unknown schema, mismatched run identity, unsafe path, invalid source hash, or unresolved evidence reference
- **WHEN** the persistence boundary validates the artifact
- **THEN** it rejects the candidate before CSV mutation
- **AND** it records a technical persistence/validation failure separately from the domain outcome.

#### Scenario: A pull-request or non-default-branch run completes
- **GIVEN** a Functional Analysis run is associated with a pull request or a non-default branch
- **WHEN** the privileged persistence workflow receives or reconciles the run
- **THEN** it rejects the run before looking up or downloading its artifacts
- **AND** the run remains available only through ordinary Actions history and its run-scoped artifact.

#### Scenario: Evidence-strength inputs are missing
- **GIVEN** the run passes its fixture oracle but lacks validated requirement-to-observation links or coverage inputs required by the selected confidence algorithm
- **WHEN** the run record is built
- **THEN** confidence is unavailable with the missing dimensions stated
- **AND** the oracle match remains only a test expectation.

#### Scenario: A run fails before producing a valid analysis result
- **GIVEN** a workflow attempt is canceled, fails during parsing, or produces a candidate rejected by validation
- **WHEN** its audit record is persisted or reconciled
- **THEN** its execution and analysis states describe what happened
- **AND** no successful domain outcome or confidence score is fabricated.

#### Scenario: Concurrent ledger writes conflict
- **GIVEN** the PoC analysis workflow and Functional Analysis writer both prepare CSV updates from the same ledger revision
- **WHEN** one writer advances the `poc-database` branch first
- **THEN** the other writer reloads the new head and reapplies its idempotent record within a bounded retry policy
- **AND** it reports persistence failure if the retry limit is exhausted without overwriting the committed record.

#### Scenario: A workflow attempt is absent from the ledger
- **GIVEN** an eligible workflow attempt completed or was canceled but no matching ledger identity exists
- **WHEN** the bounded reconciler scans the configured recovery horizon
- **THEN** it persists a validated result when the matching unexpired artifact passes all checks, or an execution-only record when no result artifact exists
- **AND** it reports an unrecoverable missing result when the necessary artifact has expired
- **AND** it does not claim reconciliation is complete while an eligible attempt remains missing or rejected.

#### Scenario: Retryable GitHub API failures exhaust their bounded retry policy
- **GIVEN** the GitHub API repeatedly returns a transient transport failure
- **WHEN** the writer performs a metadata request
- **THEN** it makes no more than three calls, each with the configured request deadline
- **AND** it reports a classified error without exposing the token or response URL.

#### Scenario: Ledger write conflicts exhaust fresh-snapshot retries
- **GIVEN** each ledger push is rejected as non-fast-forward
- **WHEN** the writer retries persistence
- **THEN** each attempt starts from a fresh ledger checkout
- **AND** after three attempts it reports persistence failure without claiming success.

#### Scenario: Recovery scan reaches its configured run bound
- **GIVEN** recent workflow history contains more runs than the configured scan limit
- **WHEN** the reconciler evaluates the API response
- **THEN** it stops before processing a partial window and reports the bound explicitly.

#### Scenario: A writer notification is lost when the concurrency queue is saturated
- **GIVEN** an eligible workflow attempt completed but its writer event was not delivered
- **WHEN** the scheduled reconciler scans recent workflow history
- **THEN** it discovers the missing run-attempt identity and records its validated result or execution-only state
- **AND** queue capacity is treated as a serialization limit, not as durable delivery.

#### Scenario: A successful run's final artifact has expired
- **GIVEN** an otherwise eligible successful workflow attempt whose expected final artifact is expired
- **WHEN** reconciliation processes the attempt
- **THEN** it records execution metadata as unreconciled without a domain outcome
- **AND** it reports reconciliation incomplete and does not attempt to download the expired artifact.
