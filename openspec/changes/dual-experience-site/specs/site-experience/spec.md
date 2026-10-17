## ADDED Requirements

### Requirement: Present distinct architecture and demo experiences
The site MUST provide clear entry points for architecture/documentation and interactive demo/workflow exploration. The two experiences MUST use a cohesive visual identity and MUST present their content with distinct information hierarchies suited to reference reading and workflow exploration respectively. Existing documentation routes, workflow actions, artifact data boundaries, and interactive explorer behavior MUST remain available.

#### Scenario: Choose a site experience
- **GIVEN** a visitor lands on the home page or opens global navigation
- **WHEN** they choose Architecture or Demo
- **THEN** they reach the corresponding documentation or workflow-explorer experience
- **AND** the destination communicates which experience they are in.

#### Scenario: Preserve workflow exploration
- **GIVEN** a visitor opens the demo
- **WHEN** they select a scenario, step, prior run, or evidence item
- **THEN** the existing explorer presents the corresponding verified data and workflow links
- **AND** presentation changes do not change artifact validation or data semantics.

### Requirement: Keep site content responsive and contained
The site MUST remain usable at narrow and wide viewport widths. Grid and flex children MUST be allowed to shrink; arbitrary-length identifiers and text MUST wrap or remain in a bounded scroll region; preformatted source MUST NOT expand the page beyond its container. Relevant layouts MUST progressively collapse for smaller viewports.

#### Scenario: Render long values in a card
- **GIVEN** a demo output contains a long path, digest, identifier, or source line
- **WHEN** it is shown in a card at a narrow viewport
- **THEN** it wraps or scrolls within its own bounded pane
- **AND** the card and page do not gain horizontal overflow.

#### Scenario: Render multi-column content on mobile
- **GIVEN** a visitor views docs or demo content on a narrow screen
- **WHEN** a multi-column grid no longer has usable column width
- **THEN** it collapses to fewer columns or one column while preserving reading order and controls.

### Requirement: Respect motion preferences
Site animations MUST remain decorative and MUST NOT obscure or delay meaningful content. When reduced motion is requested, nonessential transitions and animations MUST be removed or reduced, including the demo stage indicator.

#### Scenario: Reduced motion preference
- **GIVEN** the visitor has enabled reduced motion in the operating system
- **WHEN** any site page or demo stage is displayed
- **THEN** decorative motion is reduced or disabled and all content remains available.
