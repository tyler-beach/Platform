## Why

Pages can discover paste evaluation, but users still assemble GitHub issue bodies by hand. The next iteration should let them prepare a submission on the workflow demo page (copy body / open Issues) while GitHub remains the execution backbone, and should extract more high-confidence signals from real-looking pastes (including Kubernetes YAML snippets).

## What Changes

- Add a Pages “prepare paste submission” helper: tech-spec + code + domains + attestation → copy issue body and/or open a GitHub issue with a prepared markdown body (length-bounded; oversized pastes copy-only).
- Expand `paste_heuristic` extraction for Kubernetes YAML-ish snippets and additional grounded claims; bump extractor version.
- Keep evaluation on Issues/Actions; Pages never claims in-browser evaluation.

## Capabilities

### New Capabilities
- `paste-submit-helper`: Client-side preparation of Pathfinder analyze issue bodies from the Pages demo, with GitHub Issues as the submission surface.

### Modified Capabilities
- `paste-observation-extraction`: Broader fail-closed allowlist / YAML heuristics; version bump.
- `pages-paste-eval-bridge`: Demo panel gains prepare-and-submit controls.

## Impact

- `src/components/DemoExplorer.jsx`, `docs/javascripts/demo-explorer.js`, styles
- `.poc/requirement_engine/paste_extractor.py`, fixtures/tests
- Docs for the prepare flow
