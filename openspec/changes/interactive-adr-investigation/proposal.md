# Interactive ADR investigation workspace

## Outcome

Make the repository demo feel like a connected architecture investigation rather than a sequence of buttons and independent panels. Give visitors two concrete, language-neutral ADR examples: availability preservation through Kubernetes disruption budgets and a 60-minute maximum authenticated session lifetime.

## Scope

- Add a responsive interactive workspace linking decision, observation, candidate finding, evidence references, analysis stages, coverage gaps, and local human-review state.
- Keep synthetic examples visibly labelled and explain that local review state is not persisted.
- Add complete language-neutral ADR documents and compact synthetic fixture versions for pod disruption budgets and session TTL.
- Surface both ADR documents from the architecture hub.
- Preserve the existing generated scenario gallery, evidence validation, walkthrough, and workflow history.

## Non-goals

- Do not represent the examples as live cluster or identity-provider telemetry.
- Do not claim the new interactive review controls persist to a backend.
- Do not replace the deterministic scenario catalog or weaken its provenance validation.
- Do not prescribe a programming language or specific deployment implementation in either ADR.

## Acceptance criteria

- Visitors can switch between the two ADR examples without navigating away.
- Selecting a workflow stage updates its explanation; selecting an evidence reference updates the source reference detail.
- Human-review controls expose their selected state and state clearly that the decision is local to the demo.
- The PDB ADR requires an effective budget aligned to availability objective and replica topology, and treats missing scope evidence as inconclusive.
- The session ADR defines a 60-minute absolute maximum, prevents activity-only extension beyond the limit, and accounts for renewal behavior.
- The workspace remains usable on narrow screens and exposes controls to assistive technology.
- Existing gallery, Actions-history, provenance, and safe-rendering behavior remains intact.
