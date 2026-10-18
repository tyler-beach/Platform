# Proposal: Usable V1 Pathfinder corpus + defaults

## Why

The Go Actions spine works, but collaborators still land on a synthetic 100-ADR demo catalog, a two-ADR real pack, and mostly `inconclusive` outcomes. A usable prototype needs a believable real-looking ADR corpus as the default, better extraction coverage for that corpus, clearer intake guidance, and unaided first-run docs—while remaining replaceable by the org’s actual ADRs later.

## What Changes

- Expand `data/adr_catalog` to a ~18–20 ADR prototype corpus with typed requirements aligned to extractable predicates.
- Default catalog mode to **real**; synthetic becomes explicit opt-in (`synthetic` / demo).
- Wire catalog mode through issue form + Actions; improve domain guidance and comment coverage UX.
- Expand deterministic paste extraction where corpus gaps remain; keep model-backed extraction as a fail-closed opt-in stub (no live model required for V1).
- Collaborator first-run docs + operational trust notes (artifacts, ledger, re-run).
- Real-pack regression fixtures/sample package that produces confident (non-empty) outcomes.

## Capabilities

### New Capabilities
- (none — extends existing packs)

### Modified Capabilities
- `adr-applicability`: real pack is the product default; synthetic is demo mode.
- `issue-package-evaluation`: catalog mode from issue/workflow; coverage commentary; first-run path.
- `paste-observation-extraction`: corpus-aligned extractor coverage; optional model extract stub.
- `pages-paste-eval-bridge`: Pages copy reflects real-default prototype corpus.

## Non-goals

- Replacing the pack with the user’s private ADRs (handoff documented instead)
- Merge blocking, AWS, gRPC hosting
- Live Anthropic calls in default CI
