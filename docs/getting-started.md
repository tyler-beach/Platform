# Getting started

This repository currently contains design, contracts, Protobuf schema and documentation configuration—not a runnable deployed application. Treat these steps as the bootstrap for the first vertical slice.

## Prerequisites

- Go toolchain to be pinned by the implementation's Go module.
- Git and a local checkout.
- Buf CLI for Protobuf lint/build.
- Python with MkDocs Material for local documentation preview.

## Validate the API schema

From the repository root:

~~~sh
buf format -d
buf lint
buf build
~~~

Before merging Protobuf changes, run the compatibility check in the project Makefile from a checkout with main history available. Existing Protobuf CI covers lint, build and breaking changes for pull requests that touch the schema.

## Preview docs

~~~sh
python -m pip install -r docs-requirements.txt
mkdocs serve
~~~

Open the local URL printed by MkDocs. Swagger loads the checked-in docs/openapi.yaml; request execution is disabled by default because no live service is part of this design baseline.

## Recommended first implementation slice

1. Select one comparison mode and bind inputs to immutable source versions.
2. Implement domain types and validators from [the data contracts](contracts/CONTRACTS.md).
3. Build evidence with exact provenance before making a model call.
4. Add a fake assessor and deterministic validator tests, then a bounded structured Anthropic call behind an adapter.
5. Persist job state and audit events idempotently; test workflow-start failure recovery.
6. Make finding evidence references resolvable before adding external publication.

See [system architecture](system-architecture.md), [API behavior](contracts/API_CONTRACT.md), and [roadmap](ROADMAP.md).
