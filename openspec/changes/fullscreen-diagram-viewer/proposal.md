# Change: expand documentation diagrams for inspection

## Why

The architecture SVGs are constrained to the documentation article width, which makes their labels difficult to read. Visitors need a direct way to inspect the vector diagrams at a larger size without losing the surrounding page or relying on browser-specific image zoom gestures.

## Proposed change

Keep responsive inline diagrams and add an accessible expand action that opens the selected original SVG in a viewport-sized dialog. The dialog provides an explicit close action, supports Escape, preserves the image alternative text and caption, and returns focus to the action that opened it. If native dialog support is unavailable, open the original SVG directly. Rebind controls after MkDocs Material instant navigation while reusing the same dialog.

## Scope and non-goals

- Apply to SVG images inside `.diagram-figure` blocks across the documentation site.
- Use one shared native dialog and DOM text APIs; do not interpolate labels or captions as HTML.
- Keep diagrams visible when JavaScript is unavailable.
- Do not change SVG content, diagram meaning, Mermaid rendering, or the site's navigation.
- Do not add a new dependency or transmit image data to a service.

## Acceptance criteria

- Every supported inline diagram has a keyboard-operable, clearly labeled expand control.
- Activating a control opens that diagram's source SVG in a responsive, near-full-viewport dialog.
- The dialog retains the selected diagram's descriptive alt text and caption, closes by button or Escape, and restores focus to its opener.
- In-site instant navigation adds controls to the new page's figures without creating duplicate dialogs.
- Browsers without `HTMLDialogElement.showModal` receive the original SVG in a separate tab.
- Inline images remain responsive and readable at narrow viewport sizes.
- Node behavior tests cover discovery, selected source/description, close behavior, focus restoration, fallback behavior, and instant navigation.
- Strict MkDocs build and the Pages documentation workflow pass.

## Risks and rollback

Native dialog behavior varies slightly across browsers. The fallback opens the original scalable SVG. Roll back by removing the viewer script, its stylesheet rules, and the MkDocs script reference; the original inline diagrams remain intact.

## Decisions needing review

None. This is a presentation-only enhancement using browser-native behavior.
