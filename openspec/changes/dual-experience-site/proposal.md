# Change: redesign the site as two cohesive product experiences

## Outcome

Give ADR Deviation Platform a professional, modern SaaS-style site with two clearly signposted destinations: architecture and engineering documentation, and an interactive demo/workflow explorer. Each destination has a distinct visual hierarchy while sharing brand, navigation, accessibility, and responsive behavior.

## Scope

- Redesign the home page as a product gateway to Architecture and Demo.
- Establish a cohesive visual system for MkDocs documentation pages and the demo console.
- Improve navigation clarity, content density, cards, run history, stage walkthrough, input/evidence panes, and code presentation.
- Add subtle motion that respects reduced-motion preferences.
- Ensure long text, paths, hashes, code, and data-driven labels remain within cards and viewport widths.
- Preserve existing routes, docs, workflow links, synthetic/live-artifact data behavior, and diagram viewer behavior.

## Non-goals

- Replacing MkDocs or changing deployment, workflow artifact ingestion, data retention, or API behavior.
- Claiming live production readiness or calibrated AI quality.
- Introducing external UI dependencies, tracking, or new data transmission.

## Acceptance criteria

- Visitors can identify and navigate to Architecture and Demo from the home page and global navigation.
- Documentation pages have a readable editorial/technical treatment; the demo has a distinct, denser workflow-console treatment consistent with the same brand.
- At narrow and wide viewports, content grids collapse without horizontal page overflow; unbroken strings and source text stay contained or scroll inside their own code panes.
- Interactive demo, workflow history, stage navigation, full-screen diagram behavior, and links remain functional.
- Motion is restrained and disabled or reduced under `prefers-reduced-motion`.
- Strict MkDocs build and existing behavior tests pass; added acceptance checks verify responsive overflow protections, reduced motion, and the two destination entry points.

## Risks and rollback

A broad CSS replacement can affect Material components and third-party Swagger/Mermaid content. Keep changes in the existing local stylesheet, scope bespoke treatments to home/docs/demo roots, preserve a clear rollback diff, and run the strict site build and behavior tests. Roll back the CSS and home/nav changes independently if a surface regresses.

## Decisions needing review

None. The request explicitly authorizes a full UI rework and permits remaining on MkDocs.
