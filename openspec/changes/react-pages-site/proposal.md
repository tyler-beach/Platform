# Change: replace the MkDocs site with a React product site

## Outcome
Replace the public MkDocs Material interface with a standalone React site that feels like a modern engineering SaaS product. Architecture/documentation and demo/workflow exploration become distinct, first-class experiences with purpose-built navigation and visual hierarchy.

## Scope
- Build a React single-page application for the homepage, architecture index, reference pages, and workflow explorer.
- Render the checked-in Markdown reference content through the app and preserve access to all existing reference documents, diagrams, and API material.
- Preserve legacy documentation URLs through route aliases and a GitHub Pages fallback document.
- Keep the existing demo explorer's artifact validation, run history, synthetic scenario gallery, workflow links, and safe DOM rendering while hosting it in the React page.
- Build React assets into `site/` and keep the existing Pages workflow's data-generation, validation, security gates, and deployment stages.
- Add responsive layouts, accessible navigation and controls, restrained motion, and reduced-motion support.

## Non-goals
- Changing analysis semantics, artifact schemas, repository visibility, workflow inputs, data retention, or production architecture.
- Replacing the existing analysis/workflow engine or introducing a UI backend.
- Adding analytics, credentials, or third-party runtime services.

## Acceptance criteria
- The deployed root is served by the React app and no longer uses MkDocs Material as its UI framework.
- Architecture pages provide readable navigation, search or clear document discovery, Markdown, diagrams, and contract references.
- The Demo page presents the existing scenario gallery, sample walkthrough, evidence and confidence details, previous runs, and launch links.
- Existing legacy documentation paths resolve to their matching React reference page (or equivalent API rendering), including direct page refreshes on GitHub Pages.
- Synthetic/live workflow data continues to load from generated `site/demo/data` paths; data remains validated and is rendered as text.
- Responsive acceptance checks verify narrow layouts, long unbroken values, code panes, accessible nav controls, and reduced motion.
- The Pages workflow builds the React site, generates and validates current demo data, uploads the site, and deploys successfully.

## Risks and rollback
A framework migration can break Markdown rendering, legacy deep links, relative assets, or the artifact explorer's DOM contract. Keep existing docs and data-generation/validation scripts, use a legacy-path mapping, exercise all current JS tests, test generated data paths, and preserve the previous MkDocs workflow in Git history for rollback. Do not remove the old docs sources until the replacement has shipped and been reviewed.

## Decisions needing review
The user explicitly selected a modern framework such as React and rejected a MkDocs reskin. Use React + Vite with a static GitHub Pages build; this does not imply approval to add a service or change analysis behavior.
