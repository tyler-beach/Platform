## MODIFIED Requirements

### Requirement: Catalog identity is recorded on the report

Each evaluation report MUST include catalog identity metadata (catalog id/name, manifest hash or version, and mode such as `synthetic` or `real`) so consumers can tell which ADR pack produced the outcomes. When no catalog mode is configured, the system MUST default to the **real** prototype pack (`data/adr_catalog`). Synthetic mode MUST remain available only via explicit configuration.

#### Scenario: Report names the catalog pack
- **GIVEN** a successful package evaluation
- **WHEN** the report is written
- **THEN** it includes catalog identity fields sufficient to reproduce the pack version used

#### Scenario: Default catalog mode is real
- **GIVEN** no `--catalog-mode` flag and no `PATHFINDER_CATALOG` environment variable
- **WHEN** catalog mode is resolved
- **THEN** the resolved mode is `real`
- **AND** the catalog directory is `data/adr_catalog`
