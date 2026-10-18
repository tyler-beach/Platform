## ADDED Requirements

### Requirement: Prototype corpus predicates remain extractable without a model

For the checked-in real prototype ADR pack, the deterministic paste extractor MUST be able to emit high-confidence observations for the pack’s primary predicates from representative tech-spec and/or code fixtures, without requiring a model call. An optional model-backed extraction path MAY exist but MUST be disabled by default and MUST NOT invent observations when credentials or the enable flag are absent.

#### Scenario: Sample package yields multiple extracted observations
- **GIVEN** the real-pack sample evidence package for the prototype corpus
- **WHEN** observations are ensured with the paste extractor
- **THEN** more than one allowlisted observation is produced
- **AND** evaluation against the real pack yields at least one `supported_deviation` or `no_deviation_found` outcome

#### Scenario: Model extract stays off by default
- **GIVEN** default environment without model-extract enablement
- **WHEN** issue analysis runs
- **THEN** observation creation uses only deterministic extraction (or caller-supplied observations)
