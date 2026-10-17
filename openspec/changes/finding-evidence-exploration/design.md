# Design: citation-first evidence selection

Expose a small pure browser-core function that accepts a finding and the run's evidence array. It validates that each cited ID resolves to exactly one evidence item, returns cited items in citation order, and appends at most 40 uncited items in their original order. The display cap applies only to supplemental evidence.

The sample walkthrough exporter will include the finding's `evidence_ids` and validate that every ID exists among exported evidence. Both sample and real-run renderers use the same selector. Each card shows its evidence ID, source path and digest, with distinct text labels for cited and supplemental rows. All values continue to use `textContent`.

## Test mapping

- Node behavior tests cover citation ordering, cited evidence beyond index 40, supplemental bounds, and missing references.
- Python exporter tests cover sample finding-to-evidence references.
- Strict MkDocs and existing safe-DOM assertions cover the integrated page.
