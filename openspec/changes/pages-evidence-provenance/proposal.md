# Proposal: Require exact artifact provenance in Pages run history

## Why

The internal Pages exporter currently associates real evidence with source hashes by path. It does not validate the evidence row's `artifact_id` or verify any evidence/observation source hash against the artifact ledger. A stale, mismatched, or incomplete ledger reference can therefore be rendered as if it were pinned to an exact source version.

## What changes

- Validate artifact IDs, relative paths, and SHA-256 values before projecting internal run data.
- Require every exported evidence row to resolve by `artifact_id` to the same run's artifact row, with matching path and valid artifact SHA-256; verify its excerpt SHA-256 against the stored excerpt before redaction.
- Require every exported observation source reference to resolve to the same artifact ID, path, and SHA-256 recorded in the artifact ledger.
- Fail the real-history export closed on missing, malformed, or mismatched provenance rather than rendering an apparently auditable finding.

## Scope and non-goals

This changes only the private Pages projection of real ledger rows. It does not inspect or republish raw artifacts, change CSV schemas, or make a finding valid. It only prevents incomplete provenance from being presented as exact provenance.

## Acceptance criteria

- Missing/invalid artifact SHA-256, duplicate artifact IDs, unknown evidence artifact IDs, mismatched evidence paths, and malformed or incorrect excerpt hashes fail export.
- Unknown observation artifact IDs, mismatched paths, or source hashes fail export.
- A correct evidence and observation reference retains the full artifact SHA-256 and locator.
- The synthetic fixture exporter and public Pages gate remain unchanged.

## Risks and rollback

Older ledger rows with incomplete provenance will cause the private Pages build to fail until the source run data is repaired or a policy for explicitly marking such records inconclusive is approved. This is intentional: the exporter must not silently downgrade exact-evidence requirements.

## Decisions needing review

- Whether legacy rows lacking exact provenance should be omitted with an explicit warning or block publication. This proposal selects fail-closed behavior for now, consistent with the evidence contract.
