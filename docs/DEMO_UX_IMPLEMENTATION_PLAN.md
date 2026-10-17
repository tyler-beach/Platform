# Demo UX implementation plan

## Goal

Make the ADR Platform demo easy to understand on first visit, useful to explore without a presenter, and honest about what is illustrative versus executable.

## Changes

1. **Give the first screen one job.** Lead with the guided investigation. Keep the scenario/evidence explorer one click away, and move workflow launches into the technical section.
2. **Make evidence inspectable.** For each selected evidence item, show its illustrative source location, excerpt, what it supports, and what it cannot establish. Call out missing evidence directly.
3. **Improve playback and navigation.** Use consistent names for the five stages, slow the automatic walkthrough, and let visitors pause, resume, replay, or move between stages. Selecting evidence stops playback.
4. **Use plain language.** Describe the user-visible action and its limits; avoid claims that imply live monitoring or production enforcement.
5. **Keep technical depth available.** Preserve both the session lifetime and pod disruption budget scenarios, plus the existing PoC artifacts, workflow history, and detailed evidence output.
6. **Validate behavior.** Test the stage labels, evidence inspector, playback controls, accessible state, responsive styles, reduced-motion behavior, and synthetic-data disclosures.

## Acceptance criteria

- A first-time visitor sees a clear primary action and a separate path to deeper evidence.
- The guided example explains the decision, scope, observed values, assessment, and human review.
- Evidence details distinguish supporting facts from unknowns and explicitly label illustrative source references.
- Visitors can pause or resume playback and navigate manually; selecting evidence pauses the walkthrough.
- The copy does not imply the synthetic guided example queries live infrastructure or changes a system.
- The existing detailed PoC area remains available for visitors who want run history and implementation artifacts.

## Scope and boundaries

This is a website/demo change only. It does not change the detection engine, production architecture, ADR authority, or enforcement behavior. The guided scenarios use synthetic example data. Real PoC workflow runs remain a separate experience with their own artifacts and provenance.

## Language review

Prefer specific, conversational wording such as “See what the evidence shows” and “What this does not prove.” Avoid inflated claims such as “transformative,” vague automation promises, and internal implementation jargon in the opening screen. Keep technical terminology where it helps an engineer verify a claim.


## Pathfinder brand direction

**Name:** Pathfinder. **Tagline:** From intent to reality. **Positioning:** Keep implementation on the paved path set by architecture decisions. Use “paved path” consistently; a potential deviation is a signal to investigate, not an automatic verdict.

**Voice:** clear, grounded, and engineering-native. Prefer “Follow a paved path,” “See what changed,” “What this supports,” and “What it does not prove.” Avoid inflated claims or implying automatic enforcement.

**Palette:** Aurora `#14B8A6`, Pine `#0F766E`, Mist `#A7F3D0`, Night `#081220`, Stone `#334155`, Snow `#F8FAFC`.
