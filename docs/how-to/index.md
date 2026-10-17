# How-to guides

These guides define safe extension patterns. Turn each into a tested example as the application grows.

## [Enable the internal Pages run explorer](enable-private-pages-demo.md)

Configure organization visibility, private Pages access, the exact opt-in, and the workflow path that refreshes an audit-backed demo.

## [Add a new input source](add-input-source.md)

Bind source identity to immutable versions, preserve offsets, and validate provenance before assessment.

## [Add a Go worker](add-go-worker.md)

Keep domain transformations deterministic and effects at explicit adapter boundaries; make retries idempotent.

## [Add a comparison mode](add-comparison-mode.md)

Define input cardinality, applicability, evidence requirements, evaluation fixtures and public contract changes before implementation.

## Before opening a PR

- Propose behavior changes with OpenSpec.
- Update Protobuf and OpenAPI together if the public API changes.
- Add contract, security, replay and evaluation tests.
- Run schema lint/build/compatibility checks and docs build.
- Update runbooks and threat model when behavior or invariants change.
