# Design: separate same-origin site data from public API requests

Add a pure-boundary browser helper `fetchSiteJson(fetcher, url, siteOrigin)`. Resolve the URL, require its origin to equal the validated site origin, then issue a GET with `mode: same-origin`, `credentials: same-origin`, `redirect: error`, and `referrerPolicy: no-referrer`. Parse JSON and return clear fetch/response errors. The caller supplies the current document URL and `location.origin`.

Use the helper only for `data/sample-run.json` and `data/real-runs.json`. Keep the existing `requestJson` helper for `api.github.com` with `credentials: omit`; no GitHub token or browser Authorization header is introduced.

## Test mapping

- Node tests assert same-origin options, reject cross-origin URLs before fetch, and preserve the existing anonymous API request contract.
- Existing explorer tests and strict MkDocs build verify integration without live Pages credentials.
