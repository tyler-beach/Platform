# Design

The docs workflow computes two independent opt-ins. For each enabled path, it fetches repository and Pages metadata and applies the same fail-closed organization/private-or-internal/private-Pages guard before any protected data access. Actions history collection remains limited to workflow-runs and jobs endpoints with the existing field/run/step caps. Ledger branch cloning remains reachable only from the real-ledger opt-in.

When Actions history is enabled by itself, initialize an empty CSV store with the standard headers, collect bounded Actions metadata, and pass both to the existing history exporter. This reuses the stable `adr-demo-history-v1` contract and results in a truthful snapshot with `api_history_available: true`, workflow records present, and `runs: []`. When Actions history is disabled, do not call its API collector. When ledger export is disabled, do not look up or clone `poc-database`. Pass the checked-out `GITHUB_REPOSITORY` to the exporter even when Actions metadata is absent, so ledger-only links never fall back to the upstream repository identity.

The shared output schema already supports both collections independently: `workflow_runs` contains Actions metadata, while `runs` contains detailed ledger projections. The browser already renders the former as statuses and run links, and only expands detailed evidence for the latter.

Alternatives considered:
- Keep a shared switch: simplest setup, but unnecessarily couples low-sensitivity execution metadata to high-sensitivity evidence and finding records.
- Always collect Actions history on internal Pages: rejected because explicit opt-in and deployment behavior should remain operator-controlled.
- Separate URLs/schemas: rejected because the existing schema and renderer already distinguish the two data classes.

Failure behavior: API or visibility errors fail the build for an enabled path; disabled paths emit empty fields without API access. PR builds do not evaluate either export. No data is uploaded until the build and all validation steps succeed.
