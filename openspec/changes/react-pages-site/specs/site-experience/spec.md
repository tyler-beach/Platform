## ADDED Requirements

### Requirement: Serve the product site through a modern application shell
GitHub Pages MUST serve a standalone React application as the site's user interface. The application MUST present Architecture/reference documentation and Demo/workflow exploration as distinct first-class experiences with shared identity and independent navigation hierarchies. MkDocs Material MUST NOT be the rendered site shell.

#### Scenario: Choose an experience
- **GIVEN** a visitor opens the site root or any application page
- **WHEN** they choose Architecture or Demo in the global navigation or landing page
- **THEN** the application opens the selected experience with its own navigation and content hierarchy.

#### Scenario: Preserve the cloned repository identity
- **GIVEN** the Pages build runs from a private organization clone
- **WHEN** the application renders repository and workflow links
- **THEN** those links use the validated clone identity supplied by the build and do not direct the visitor to the original public repository.

#### Scenario: Direct-load a legacy documentation URL
- **GIVEN** a visitor opens or refreshes a previously published documentation URL
- **WHEN** GitHub Pages serves the static application fallback
- **THEN** the client route resolves to the corresponding existing reference document or API view.

### Requirement: Preserve reference content and safe rendering
The application MUST expose the checked-in reference documents, diagrams, API contract, and supporting assets. Relative document links and assets MUST resolve within the application. Markdown rendering MUST sanitize raw HTML. Artifact contents MUST continue to be treated as untrusted data and MUST NOT be interpreted as executable HTML or instructions.

#### Scenario: Open a Markdown reference
- **GIVEN** a visitor selects an architecture, contract, or engineering reference
- **WHEN** the route loads directly or through navigation
- **THEN** the document renders with headings, lists, tables, code, diagrams, and working local links.

#### Scenario: Render hostile artifact text
- **GIVEN** a validated artifact contains HTML-like source text
- **WHEN** the workflow explorer presents it
- **THEN** it is displayed as inert text and cannot execute markup or script.

### Requirement: Keep workflow explorer behavior and data paths
The React Demo experience MUST expose scenario selection, synthetic walkthrough, evidence/confidence/coverage views, prior workflow runs, and workflow launch links. It MUST load build-generated demo data from stable same-origin paths independent of the current nested route. Existing run/artifact validation MUST remain in force.

#### Scenario: Load generated demo data at a deep route
- **GIVEN** the site is deployed beneath a GitHub Pages project path
- **WHEN** a visitor opens or refreshes the Demo route
- **THEN** the sample run, scenario gallery, and run-history data load from the deployed site's generated data files.

#### Scenario: Revisit the Demo route
- **GIVEN** a visitor navigates away from and back to the Demo route without a full reload
- **WHEN** the explorer mounts again
- **THEN** controls work once, no duplicate event handlers or playback timers remain, and validated content renders normally.

### Requirement: Provide responsive, accessible behavior
The application MUST remain usable at desktop and mobile widths, contain arbitrary-length data, provide keyboard-visible focus and semantic navigation, and respect reduced-motion settings.

#### Scenario: Narrow viewport with long content
- **GIVEN** a visitor views reference or workflow content on a narrow screen containing a long digest or source line
- **WHEN** the content is displayed
- **THEN** columns collapse and text wraps or scrolls inside a bounded code pane without horizontal page overflow.

#### Scenario: Reduced motion
- **GIVEN** reduced motion is enabled
- **WHEN** an application page is displayed
- **THEN** decorative animations and transitions are removed or substantially reduced without hiding content.
