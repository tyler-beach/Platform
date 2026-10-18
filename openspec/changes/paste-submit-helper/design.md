## Goals

- From `/demo`, paste tech-spec/code → copy a form-compatible issue body → open GitHub Issues.
- Prefer `issues/new` with title/labels/body when under URL size budget; otherwise copy + open template.
- Expand deterministic extraction without inventing negatives.

## Non-goals

- Evaluating paste contents in the browser
- Uploading paste content to Pages storage
- Prefilling GitHub issue-form field IDs (unsupported / fragile)

## Issue body shape

Emit the same `###` sections the Actions parser already understands:

- Public / synthetic attestation (`- [X] ...`)
- Domains
- Tech spec (markdown)
- Sample code
- Observations left empty (extractor fills on Actions)

## Extractor v2

Add YAML/manifest heuristics for replicas/probes/PDB when the paste looks like Kubernetes YAML. Keep conflict/silence fail-closed. Version → `paste-heuristic-v2`.
