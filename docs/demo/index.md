# Workflow demo

The interactive **React workflow explorer** lives at /demo/. It presents the checked-in synthetic scenario gallery, the deterministic mock walkthrough, evidence and confidence details, recent verified workflow history, and links to launch the GitHub Actions workflows.

The explorer is implemented in src/components/DemoExplorer.jsx and uses the audited renderer in docs/javascripts/demo-explorer.js. Pages builds populate its same-origin data files under site/demo/data/; the React app serves this view at the previous /demo/ route.

All curated examples use synthetic fixtures. Live artifact inputs are displayed only after the existing workflow identity, digest, hash, evidence, and fixture-path checks pass. Source and artifact contents remain inert text. Evidence support scores are not calibrated probabilities, and Functional Analysis runs do not claim a confidence score.

## Expanded technical examples

Use these longer examples to follow multiple requirements through evidence, findings, and API payloads rather than inspect a single isolated case.

- [Session Management Service: multi-requirement technical specification](realistic-session-service.md) — ten requirements, four ADRs, mixed alignments, deviations, potential findings and inconclusive cases, reviewer actions, and an evidence-linked finding envelope.
- [API response mockups](api-payload-examples.md) — contract-shaped job acceptance, lifecycle polling, findings with immutable evidence references, an inconclusive result, and a stable 409 error response.
- [Finding review playbook](finding-review-playbook.md) — how to interpret outcome categories, validate evidence and revisions, challenge inferences, and record human dispositions.

The examples use synthetic source data. The API contract is the production target; these payloads are mock responses, not responses from a running service.
