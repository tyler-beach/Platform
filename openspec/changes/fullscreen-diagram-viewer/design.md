# Design: expandable architecture diagrams

## Current behavior

Architecture SVGs are displayed inline in `.diagram-figure` figures. CSS scales them to the documentation content width and clips overflow. There is no larger view action. The site already ships a small amount of local JavaScript and has Node's built-in test runner available.

## Proposed interaction

At initialization, a dedicated `diagram-viewer.js` finds SVG images inside `.diagram-figure` elements. It adds an inline “Expand” button to each figure and creates one shared native `<dialog>` with a title, caption, responsive image, and close button. The selected figure's image source, alt text and caption are copied using DOM properties and `textContent`, not HTML templates. Native dialog behavior provides modal focus handling and Escape support; on close the script focuses the original button. If `showModal` is missing, the button opens the original SVG in a separate tab.

MkDocs Material's `document$` observable re-runs discovery after instant navigation. The viewer stores its dialog on the dialog element and skips figures that already have a button, keeping repeated initialization idempotent. If `document$` is unavailable, it initializes once after `DOMContentLoaded` (or immediately when the document is ready).

The inline SVG remains in place as the no-JavaScript and narrow-screen fallback. CSS makes the button visible and touch-friendly, styles the dialog to use nearly the full viewport, and constrains the SVG by both viewport dimensions while preserving its vector aspect ratio.

## Failure and security considerations

- If a figure lacks an image source, no expand control is added.
- If no figures exist on a page, the script adds no dialog or UI.
- Caption and alt text are treated as text; no artifact or user-provided HTML is interpreted.
- No fetch, external library, credential, or additional network request is introduced.
- The existing inline figure stays usable if script initialization fails.

## Test proof

`docs/javascripts/diagram-viewer.test.cjs` exercises the viewer with a minimal DOM harness: figure discovery and no-op behavior, correct selected SVG and description, explicit and Escape close with focus return, the no-dialog fallback, and repeat initialization after instant navigation. `mkdocs build --strict` verifies the documentation configuration and generated pages.

## Rollback

Remove `diagram-viewer.js` from MkDocs, remove its styles, and delete the test/workflow invocation. The inline diagrams are unchanged.
