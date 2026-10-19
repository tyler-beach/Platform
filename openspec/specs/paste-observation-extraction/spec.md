# paste-observation-extraction Specification

## Purpose
Fail-closed normalization of allowlisted typed catalog observations from pasted evidence so issue analysis can evaluate without hand-authored observation JSON. Deterministic extraction is the default; semantic extraction is an explicit bounded opt-in.
## Requirements
### Requirement: Extract typed observations from pasted tech-spec or code

When an evidence package includes tech_spec and/or code content and does not supply observations, the system MUST normalize it at the evaluation boundary. By default it runs a deterministic paste extractor that emits zero or more typed observations for allowlisted catalog predicates. Extraction MUST NOT call a model unless the explicit semantic opt-in is enabled. Observations MUST use catalog subjects, preserve the source-derived evidence role, and pin artifact digests/locators. The deterministic paste extractor MUST recognize high-confidence Kubernetes YAML-style claims for allowlisted predicates such as deployment replicas and probe/PDB presence when those keys appear explicitly in pasted text. The extractor version MUST identify the heuristic revision used.

#### Scenario: Markdown tech spec yields extractable observations
- **GIVEN** a package with only markdown tech-spec content describing session TTL and encryption at rest, and no observations array
- **WHEN** extraction and package evaluation run
- **THEN** observations for the matched allowlisted predicates are present
- **AND** catalog evaluation produces at least one non-inconclusive outcome for those predicates

#### Scenario: Code paste detects secret-in-source without inventing absence
- **GIVEN** Python or Go source containing a hardcoded API key-like secret literal
- **WHEN** extraction runs
- **THEN** `security.secret_in_source.present` is emitted as `true` with a span locator
- **AND** source that contains no secret match does not emit `security.secret_in_source.present=false`

#### Scenario: Conflicting values within a role fail closed
- **GIVEN** one artifact that asserts two different numeric values for the same predicate and subject
- **WHEN** extraction runs
- **THEN** no observation is emitted for that predicate+subject

#### Scenario: Cross-role disagreement is preserved
- **GIVEN** a tech spec and a code artifact assert different values for the same predicate and subject
- **WHEN** extraction runs
- **THEN** each observation is retained with its artifact-derived role
- **AND** each role is evaluated independently

#### Scenario: Issue intake accepts paste without observations JSON
- **GIVEN** a Pathfinder analyze issue with attestation, tech spec and/or code, and no observations JSON
- **WHEN** issue analysis evaluates the pinned package
- **THEN** extraction or semantic normalization runs according to the configured mode
- **AND** evaluation proceeds (empty extraction yields inconclusive coverage, not an intake hard-fail for missing observations)

#### Scenario: Kubernetes YAML snippet yields replica observation
- **GIVEN** pasted YAML containing `replicas: 2` under a Deployment-like snippet
- **WHEN** extraction runs
- **THEN** `kubernetes.deployment.replicas` is emitted with value `2`
- **AND** the extractor version identifies the current heuristic revision

### Requirement: Prototype corpus predicates remain extractable without a model

For the checked-in real prototype ADR pack, the deterministic paste extractor MUST be able to emit high-confidence observations for the pack’s primary predicates from representative tech-spec and/or code fixtures, without requiring a model call. An optional semantic extraction path MAY exist but MUST be disabled by default and MUST NOT claim semantic coverage when credentials or the enable flag are absent.

#### Scenario: Sample package yields multiple extracted observations
- **GIVEN** the real-pack sample evidence package for the prototype corpus
- **WHEN** observations are ensured with the paste extractor
- **THEN** more than one allowlisted observation is produced
- **AND** evaluation against the real pack yields at least one `supported_deviation` or `no_deviation_found` outcome

#### Scenario: Model extract stays off by default
- **GIVEN** default environment without model-extract enablement
- **WHEN** issue analysis runs
- **THEN** observation creation uses only deterministic extraction (or caller-supplied observations)

