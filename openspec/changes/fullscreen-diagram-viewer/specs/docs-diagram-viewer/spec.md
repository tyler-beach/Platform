## ADDED Requirements

### Requirement: Expand documentation diagrams accessibly

The documentation site MUST keep each architecture SVG visible inline and provide a clearly labeled, keyboard-operable action to inspect it at a larger size. Activating the action MUST display the selected SVG in a responsive modal dialog that preserves its aspect ratio, accessible description, and figure caption. The dialog MUST provide a close control, close on Escape, and return focus to the action that opened it. If native modal dialogs are unavailable, the action MUST open the original SVG in a separate tab. The implementation MUST use safe DOM text APIs for captions and labels and MUST NOT add an external dependency or send diagram content to a remote service.

When MkDocs Material instant navigation is enabled, the viewer MUST initialize for newly navigated page content and MUST reuse one dialog rather than adding duplicates.

#### Scenario: Open a selected diagram
- **GIVEN** an architecture page contains multiple `.diagram-figure` SVGs
- **WHEN** a visitor activates the expand control for one figure
- **THEN** the viewer opens that figure's original SVG in a viewport-sized dialog
- **AND** the dialog displays that figure's alt text and caption
- **AND** no other figure is substituted for the selected one.

#### Scenario: Close the viewer with keyboard or control
- **GIVEN** the diagram dialog is open
- **WHEN** the visitor presses Escape or activates the close control
- **THEN** the dialog closes
- **AND** keyboard focus returns to the expand control that opened it.

#### Scenario: Fallback when native dialog support is absent
- **GIVEN** the browser does not support `showModal`
- **WHEN** the visitor activates an expand control
- **THEN** the original SVG opens in a separate tab
- **AND** the inline diagram remains visible on the documentation page.

#### Scenario: Preserve responsive inline access
- **GIVEN** the visitor has not opened the expanded viewer or JavaScript is unavailable
- **WHEN** the documentation page is viewed at a narrow or wide viewport
- **THEN** the inline SVG remains contained within its figure and scales to the available width.

#### Scenario: Navigate to diagrams without a full page reload
- **GIVEN** the visitor is using MkDocs Material instant navigation
- **WHEN** the site replaces the current page with an architecture page
- **THEN** each new diagram receives an expand control
- **AND** the viewer reuses a single dialog for the page.
