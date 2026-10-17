# Proposal: Load Pages snapshots with same-origin authentication

## Why

The demo fetches `sample-run.json` and `real-runs.json` with Fetch `credentials: omit`. On a privately published Pages site, snapshot requests may need the authenticated same-origin browser session granted to a repository reader. Omitting all credentials can prevent the page from loading its own static snapshots, disabling both the walkthrough and the internal run explorer.

## What changes

- Add a same-origin-only snapshot fetch helper that sends credentials only to the Pages origin.
- Use it for the synthetic walkthrough and bounded run-history snapshot.
- Keep GitHub API requests credential-free, and reject snapshot URLs whose origin differs from the site origin.
- Test that the Pages origin receives same-origin credentials while a cross-origin URL is rejected and GitHub API requests still use `omit`.

## Scope and non-goals

This changes browser fetch behavior for static site data only. It does not add a browser token, broaden GitHub API access, change the real-data gate, or authorize any external origin.

## Acceptance criteria

- Same-origin Pages JSON requests use Fetch `credentials: same-origin`.
- A cross-origin snapshot URL is rejected before invoking `fetch`.
- GitHub API calls continue to use `credentials: omit` and contain no Authorization header.
- The public fixture and private Pages snapshot paths use the same helper.

## Risks and rollback

The private Pages flow cannot be exercised against this public upstream. Local contract tests prove origin enforcement and request options; end-to-end private authentication still needs verification in the user's internal clone.

## Decisions needing review

None. This applies credentials only to the exact same origin that served the page.
