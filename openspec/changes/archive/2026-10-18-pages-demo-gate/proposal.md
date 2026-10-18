## Why

The public GitHub Pages demo is wide open to scrapers that can discover Issue/Actions deep-links. A lightweight shared-passphrase gate reduces casual and low-level bot traffic without implying real authentication.

## What Changes

- Add a client-side passphrase gate for the Pages React app (and `pathfinder-flow/`) when a build-time secret is configured.
- Unlock state persists in `sessionStorage` for the browser tab/session.
- When no passphrase is configured (local/CI), the gate is disabled so builds and tests remain open.
- Document that this is friction only—not access control—and GitHub Issues remain independently reachable.

## Capabilities

### New Capabilities
- `pages-demo-gate`: Optional shared-passphrase gate for the published Pages demo surfaces.

## Impact

- `src/demoGate.js`, `src/components/DemoGate.jsx`, `src/main.jsx`
- `public/pathfinder-flow/index.html`, build scripts, `docs.yml`
- Repo secret `DEMO_GATE_PASSPHRASE` (optional)
