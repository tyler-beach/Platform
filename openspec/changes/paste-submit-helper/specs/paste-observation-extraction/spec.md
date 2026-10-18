## MODIFIED Requirements

### Requirement: Extract typed observations from pasted tech-spec or code

The paste extractor MUST also recognize high-confidence Kubernetes YAML-style claims for allowlisted predicates such as deployment replicas and probe/PDB presence when those keys appear explicitly in the pasted text. The extractor version MUST identify the heuristic revision used.

#### Scenario: Kubernetes YAML snippet yields replica observation
- **GIVEN** pasted YAML containing `replicas: 2` under a Deployment-like snippet
- **WHEN** extraction runs
- **THEN** `kubernetes.deployment.replicas` is emitted with value `2`
- **AND** the extractor version identifies the current heuristic revision
