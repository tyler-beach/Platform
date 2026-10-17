# Proposal: Demoable PoC workflow explorer on GitHub Pages

## Outcome

Make the GitHub Actions PoC understandable in live demos: explain the implementation and limits, animate pipeline stages, show detailed run records with evidence and confidence components, and browse recent workflow/job/step status.

## Why now

The repository has a documentation site and runnable workflows, but it describes the design mostly as static prose. A demo should connect a real Actions run to its stages and outputs without implying the proposed AWS production architecture exists.

## Scope

- Add an interactive demo page to the existing MkDocs Material site.
- Generate a deterministic fixture walkthrough from the checked-in synthetic Go project using the mock provider.
- When explicitly enabled on a private repository with private Pages access verified by GitHub's Pages API, package real CSV run data from the `poc-database` branch into the site.
- Browse recent workflow run/job/step status from the read-only GitHub REST API and match run IDs to detailed site data where available.
- Add accessible stage playback, evidence/confidence/coverage exploration, docs CI tests, and automatic Pages rebuild after analysis.

## Non-goals

- No PAT, GitHub App token, GITHUB_TOKEN, or other secret in browser code or generated site data.
- No prompts, credentials, provider request/response payloads, raw workflow artifacts, or unbounded CSV export.
- No production AWS workflow, API, hosted database, or live model call.
- No claim that evidence-strength scores are calibrated probabilities.

## Design challenge and trade-offs

An interactive page that downloads workflow artifacts directly requires authentication and can expose more than a demo needs. A fixture-only site cannot show that prior workflows actually ran. This design combines GitHub's read-only run/job API with a bounded server-built view of the audit ledger. The latter may include real PoC evidence excerpts because the user intends to move the project into a private organization and use internal-only Pages.

Real run data is fail-closed: the repo must be private, the Pages API must report `public: false`, and `PAGES_REAL_RUN_DATA_ENABLED=true` must be explicitly set. Public builds contain only the synthetic fixture walkthrough. Source excerpts are redacted for quoted literals and credential-shaped patterns; original artifact hashes and locators remain visible. This reduces accidental disclosure while preserving the source version trail.

The API history remains subject to rate limits and network failure. The synthetic walkthrough remains available independently and is never mislabeled as the latest real run.

## Open decisions

- The user authorized real POC run records for a future private/internal Pages deployment. Live publishing is not enabled in this public checkout; it requires the private clone, internal Pages setting, and explicit repo variable.
- Numeric confidence remains an evidence-support score, not a probability.
- The `poc-database` branch remains an append-only PoC CSV ledger, not a transactional database or production API.

## Acceptance

- Strict MkDocs build renders the demo page and all linked assets.
- Docs CI generates a fixture walkthrough from actual offline PoC output, not hand-authored results.
- Tests cover snapshot field/size allowlists, evidence redaction, out-of-scope paths, API validation/escaping/fallback, timeline order, and reduced motion.
- The site explains how to launch both workflows, inspect outputs, and interpret the evidence-strength score.
- Private/internal Pages builds can include detailed actual run records and update after PoC analysis; every other configuration either stays fixture-only or fails closed when real-data mode was explicitly enabled.
- Do not claim a remote Pages deployment until it is observed in the target private organization.
