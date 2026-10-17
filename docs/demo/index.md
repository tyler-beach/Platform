# Workflow demo

The interactive **React workflow explorer** lives at `/demo/`. It presents the checked-in synthetic scenario gallery, the deterministic mock walkthrough, evidence and confidence details, recent verified workflow history, and links to launch the GitHub Actions workflows.

The explorer is implemented in [`src/components/DemoExplorer.jsx`](../../src/components/DemoExplorer.jsx) and uses the audited renderer in `docs/javascripts/demo-explorer.js`. Pages builds populate its same-origin data files under `site/demo/data/`; the React app serves this view at the previous `/demo/` route.

All curated examples use synthetic fixtures. Live artifact inputs are displayed only after the existing workflow identity, digest, hash, evidence, and fixture-path checks pass. Source and artifact contents remain inert text. Evidence support scores are not calibrated probabilities, and Functional Analysis runs do not claim a confidence score.
