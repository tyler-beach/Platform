# Design: two cohesive site experiences

## Direction

Keep MkDocs Material as the content, search, route, and deployment engine. A bespoke app rewrite would duplicate routing/search and put working workflow explorer behavior at risk without improving the needed outcomes. Use the home page as a full-width product gateway; group top-level navigation around **Architecture** and **Demo**, with supporting API and Engineering references nested in docs navigation. The docs experience uses a bright editorial canvas, legible line lengths, calm surfaces, and technical diagrams. The demo experience uses a denser dark console header, high-contrast status surfaces, scenario selection, workflow timeline, and source/evidence panes. Shared typography, accent color, spacing, borders, and focus styles keep the experiences related.

## Layout and responsive behavior

- Retain demo DOM IDs and data-driven render targets; style by page root rather than restructuring script contracts.
- Make all grid children `min-width: 0`; use `overflow-wrap: anywhere` for hashes, identifiers, and arbitrary data, and constrain preformatted source to its own horizontal scroll region.
- Collapse multi-column content progressively at tablet/mobile widths. Action clusters wrap, status metadata may wrap, and no fixed-width card may expand the page.
- Keep MkDocs side navigation/search on documentation pages; home and demo can use wider page canvases while retaining the global header/tabs.
- Preserve accessible labels, keyboard operation, focus indicators, and the existing diagram modal.

## Motion

Use short CSS transitions for navigation, cards, and state changes, plus a restrained reveal/ambient treatment that does not delay content. Avoid animation in data that could imply live execution. Respect `prefers-reduced-motion` globally and on the existing stage progress track.

## Alternatives considered

1. **Stay on stock MkDocs styling.** Lowest maintenance but does not deliver the requested differentiated product feel.
2. **Move to a bespoke static frontend.** Adds routing/search/build ownership and increases regression risk to run history/artifact exploration. MkDocs already supports custom page framing and local CSS/JS, so this is unnecessary for the requested visual outcomes.
3. **Use an external component framework/theme.** Adds dependency and could change site behavior; current CSS and DOM already express the required experiences.

## Security and operations

This is presentation-only. Continue using text-safe DOM rendering in the demo explorer; source/artifact strings remain untrusted data. Do not add network calls, analytics, credentials, or executable content. Preserve synthetic/live artifact verification boundaries and current workflow endpoints.

## Acceptance proof

Node static acceptance tests check for clear Architecture/Demo entry points, constrained text/code panes, and reduced-motion handling. Existing demo explorer and diagram viewer behavior tests protect interactions. `mkdocs build --strict` checks routes/configuration/content rendering. Visual review uses locally generated output if a local browser is available; external Pages inspection is not part of this change.
