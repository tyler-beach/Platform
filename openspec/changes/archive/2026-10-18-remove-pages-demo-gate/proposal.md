## Why

The optional Pages shared-passphrase gate only stores an unlock flag and publishes a hash in `demo-gate.json`. That is not meaningful protection and is not worth operating.

## What Changes

- Remove the client-side demo gate from the React app and `pathfinder-flow/`.
- Remove build/secret wiring for `DEMO_GATE_PASSPHRASE`.
- Remove the `pages-demo-gate` current-state capability.

## Capabilities

### Removed Capabilities
- `pages-demo-gate`

## Impact

- Pages site returns to ungated public demo
- Docs no longer instruct setting `DEMO_GATE_PASSPHRASE`
