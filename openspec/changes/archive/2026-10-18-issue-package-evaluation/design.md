## Goals

- User opens `[Pathfinder analyze]` issue → Actions evaluates catalog → bot comments results.
- Support full package JSON or form fields that assemble a package.
- Keep comments reference-heavy; full report in workflow artifacts.

## Non-goals

- Automatic NL extraction of observations from free prose (observations still required or provided in package JSON).
- Private/confidential production source in public issues.

## Flow

1. Issue opened/edited/labeled with analyze marker
2. Parse package from body
3. Validate schema + size limits + attestation
4. `evaluate_package`
5. Comment summary + top findings; upload artifact
