## Goals

- Shared passphrase unlock before browsing demo surfaces when configured.
- No gate when secret unset (dev/CI).
- Compare SHA-256 of passphrase (not store plaintext preference in session beyond unlock flag).

## Non-goals

- Real authN/authZ, per-user accounts, private Pages
- Stopping direct GitHub Issues/API abuse
- Hiding the passphrase from determined readers of the built JS/config

## Flow

1. Build writes `demo-gate.json` with `{enabled, hash}` from `DEMO_GATE_PASSPHRASE` / `VITE_DEMO_GATE_PASSPHRASE`
2. App loads config; if disabled → render normally
3. If enabled and session unlocked → render normally
4. Else show passphrase form; on match set `sessionStorage` and continue
5. `pathfinder-flow/` uses the same config + session key
