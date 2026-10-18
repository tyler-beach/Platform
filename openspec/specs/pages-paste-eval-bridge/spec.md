# pages-paste-eval-bridge Specification

## Purpose
GitHub Pages workflow demos deep-link paste→catalog evaluation that executes on Issues/Actions, and may show a redacted build-time fixture snapshot without embedding source bodies.
## Requirements
### Requirement: Pages surface paste evaluation through GitHub backbone

The GitHub Pages workflow demos MUST explain and deep-link paste→catalog evaluation that executes on GitHub Issues and Actions. Pages MAY show a redacted, build-time snapshot from checked-in fixtures, but MUST NOT claim in-browser evaluation or embed full tech-spec/code bodies from the fixtures.

#### Scenario: Demo page links to analyze issue and workflow
- **GIVEN** the published `/demo` page
- **WHEN** a visitor inspects the paste evaluation section
- **THEN** links exist to the Pathfinder analyze issue form and the `pathfinder-issue-analyze` workflow
- **AND** copy states that GitHub Issues/Actions perform the live evaluation

#### Scenario: Build publishes a redacted paste-eval snapshot
- **GIVEN** the Pages documentation build
- **WHEN** paste-eval snapshot export runs against checked-in fixtures
- **THEN** `site/demo/data/paste-eval-snapshot.json` is produced
- **AND** the snapshot includes aggregate status and extracted predicate names/values
- **AND** the snapshot does not include full tech-spec or code source bodies

