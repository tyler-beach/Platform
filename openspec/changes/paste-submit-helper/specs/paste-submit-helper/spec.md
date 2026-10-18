## ADDED Requirements

### Requirement: Prepare a Pathfinder analyze issue body from the Pages demo

The workflow demo page MUST provide controls to assemble a Pathfinder analyze issue body from tech-spec text, optional sample code, optional domains, and a required public/synthetic attestation. The page MUST offer copy-to-clipboard of that body and a control that opens GitHub Issues. When the prepared body fits a safe URL budget, the open control MAY include the body in the issue URL; otherwise it MUST copy the body and open the analyze issue template without claiming the paste was uploaded to Pages.

#### Scenario: Copy prepared issue body
- **GIVEN** a visitor on `/demo` who enters tech-spec text and checks the attestation box
- **WHEN** they activate Copy issue body
- **THEN** the clipboard receives markdown with attestation, tech-spec, and empty observations guidance compatible with issue intake parsing

#### Scenario: Open GitHub without browser evaluation
- **GIVEN** a prepared paste submission on `/demo`
- **WHEN** the visitor opens GitHub from the helper
- **THEN** a GitHub Issues URL for the repository is opened
- **AND** the page does not claim the catalog was evaluated in the browser

## MODIFIED Requirements

### Requirement: Extract typed observations from pasted tech-spec or code

The paste extractor MUST also recognize high-confidence Kubernetes YAML-style claims for allowlisted predicates such as deployment replicas and probe/PDB presence when those keys appear explicitly in the pasted text. The extractor version MUST identify the heuristic revision used.

#### Scenario: Kubernetes YAML snippet yields replica observation
- **GIVEN** pasted YAML containing `replicas: 2` under a Deployment-like snippet
- **WHEN** extraction runs
- **THEN** `kubernetes.deployment.replicas` is emitted with value `2`
- **AND** the extractor version identifies the current heuristic revision
