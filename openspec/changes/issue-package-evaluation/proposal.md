## Why

The multi-ADR catalog can evaluate a pinned evidence package, but users still cannot submit their own tech spec/code through GitHub. The prototype needs an inbound issue path that builds a package, runs catalog evaluation, and comments results.

## What Changes

- Add a Pathfinder analyze issue form for tech spec, optional code, domains, and observations JSON (or a full `pathfinder-package` JSON block).
- Add a GitHub Actions workflow triggered by analyze issues that pins inputs, runs `evaluate_package.py`, uploads the report artifact, and comments aggregate + per-requirement outcomes without echoing full source into the thread.
- Enforce size limits and public/synthetic attestation; fail closed on invalid packages.

## Capabilities

### New Capabilities
- `issue-package-evaluation`: GitHub issue intake for evidence-package evaluation against the typed ADR catalog.

## Impact

- `.github/ISSUE_TEMPLATE/`, `.github/workflows/`, `.poc/issue_analyze/`
- Docs for how to submit a real (synthetic/public) package via Issues
- Public-repo safety: no secrets/excerpts required in result comments
