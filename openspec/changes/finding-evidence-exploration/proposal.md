# Proposal: Connect finding citations to evidence in the demo explorer

## Why

The exported run projection now validates that conclusive findings cite evidence IDs, but the browser does not use those IDs. The evidence panel shows up to 40 records in ledger order without distinguishing finding citations from other run evidence. A cited item beyond the first 40 can be hidden, leaving the displayed conclusion difficult to audit.

## What changes

- Display every evidence record cited by the finding before supplemental evidence.
- Label cards as finding citations or additional run evidence, and show the evidence ID.
- Limit supplemental cards to 40 while never truncating cited evidence.
- Apply the same behavior to the synthetic walkthrough and the internal run explorer.
- Fail clearly if a displayed conclusive record refers to an evidence ID that is missing from its snapshot.

## Scope and non-goals

This changes only evidence selection and presentation in the static demo. It does not change finding policy, evidence collection, assessment behavior, or Pages visibility gates.

## Acceptance criteria

- All cited evidence IDs appear in the explorer even when they occur after the first 40 ledger rows.
- Cited evidence is visually labelled and appears before supplemental evidence.
- At most 40 uncited evidence records are shown.
- Missing citations produce a visible data-integrity error rather than silently omitting the reference.
- Synthetic and internal run views behave consistently.

## Risks and rollback

Runs with unusually many citations may produce a long evidence panel. All cited references remain available because omitting a citation would make the finding harder to audit.

## Decisions needing review

None. This presentation follows the accepted evidence-first rule and does not change finding semantics.
