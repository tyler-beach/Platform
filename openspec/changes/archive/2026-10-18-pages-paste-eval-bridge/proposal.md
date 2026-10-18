## Why

Paste→catalog evaluation now runs on GitHub Issues/Actions, but the GitHub Pages workflow demos never surface it. Users testing on `/demo`, `pathfinder-flow/`, and `/evaluation` still only see older PoC workflows and cannot discover or exercise the paste path from those pages.

## What Changes

- Build a redacted paste-evaluation demo snapshot from checked-in messy fixtures (no source bodies) during Pages build.
- Surface the snapshot on the workflow demo pages with clear “GitHub is the backbone” copy.
- Deep-link CTAs to the Pathfinder analyze issue form and `pathfinder-issue-analyze` workflow.
- Include the analyze workflow in demo Actions history allowlist.

## Capabilities

### New Capabilities
- `pages-paste-eval-bridge`: Pages surfaces for discovering and testing paste→catalog evaluation via GitHub Issues/Actions.

## Impact

- `.poc/demo/export_paste_eval_snapshot.py`, `.github/workflows/docs.yml`
- `src/components/DemoExplorer.jsx`, `EvaluationDashboard.jsx`, `docs/javascripts/demo-explorer.js`
- `public/pathfinder-flow/index.html`, docs/tests
- No browser-side evaluation; Issues/Actions remain the execution path
