## Goals

- Let users try paste evaluation from Pages while GitHub Issues + Actions remain the execution backbone.
- Show a previously computed, redacted fixture result on Pages for orientation.
- Never claim in-browser evaluation or paste arbitrary user source into public Pages storage.

## Non-goals

- Pyodide/WASM evaluation in the browser
- Accepting free-form paste uploads into Pages
- Expanding extractor allowlists (separate change)

## Flow

1. Docs build runs `export_paste_eval_snapshot.py` on checked-in fixtures
2. Snapshot JSON lands in `site/demo/data/paste-eval-snapshot.json` (predicates/outcomes only)
3. Demo pages render snapshot + CTAs to issue template / Actions workflow
4. Live evaluation still happens only when the user opens/submits a GitHub issue
