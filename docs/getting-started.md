# Getting started

This repository contains a design baseline and a runnable GitHub Actions proof of concept. It is not a deployed production application. To run the current PoC, follow [Executable PoC](EXECUTABLE_POC.md) and explore the [interactive demo](demo/index.md). The steps below cover the React Pages application and contract checks while production implementation remains on the roadmap.

## Prerequisites

- Go toolchain to be pinned by the implementation's Go module.
- Git and a local checkout.
- Buf CLI for Protobuf lint/build.
- Node.js 22+ for the React/Vite site, plus Python for contract validation.

## Validate the API schema

From the repository root:

~~~sh
buf format -d
buf lint
buf build
~~~

Before merging Protobuf changes, run the compatibility check in the project Makefile from a checkout with main history available. Existing Protobuf CI covers lint, build and breaking changes for pull requests that touch the schema.

## Run the site locally

~~~sh
python -m pip install -r docs-requirements.txt
npm ci
npm run dev
~~~

Open the local URL printed by Vite. Architecture references are bundled from `docs/`; the API source is the checked-in `docs/openapi.yaml`. No live API service is part of this design baseline.

## Recommended first implementation slice

1. Select one comparison mode and bind inputs to immutable source versions.
2. Implement domain types and validators from [the data contracts](contracts/CONTRACTS.md).
3. Build evidence with exact provenance before making a model call.
4. Add a fake assessor and deterministic validator tests, then a bounded structured Anthropic call behind an adapter.
5. Persist job state and audit events idempotently; test workflow-start failure recovery.
6. Make finding evidence references resolvable before adding external publication.

See [system architecture](system-architecture.md), [API behavior](contracts/API_CONTRACT.md), and [roadmap](ROADMAP.md).
