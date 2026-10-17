# Design: React Pages product site

## Framework and build
Use React 19, Vite, React Router, React Markdown with GFM, and a sanitizer for locally authored raw HTML in Markdown. Build a static bundle into `site/`. Keep Markdown under `docs/` as the source of truth and import it at build time; copy `docs/assets/` to the output so relative images and diagrams remain available. No runtime Markdown fetch or content API is required. Use React Router with the project Pages basename and emit `404.html` from the built app so direct deep links and refreshes work on GitHub Pages.

## Information architecture
- Global shell: recognizable platform mark, Architecture and Demo destinations, repository link, compact mobile menu.
- Home: product narrative and two prominent, visually distinct destination cards.
- Architecture experience: left-side document navigation and search, selected document content, section table of contents; categories include system architecture, decisions, contracts, engineering guides, API, and operations.
- Demo experience: a distinct dark workflow-console header and light high-contrast data surfaces; a sidebar/index or stage rail directs visitors through scenario gallery, walkthrough, evidence, workflow run history, and launch instructions.
- Legacy routes map to their existing Markdown files so old bookmarks and internal links continue to work.

## Markdown and assets
Use React Markdown + GFM. Permit checked-in HTML only through raw parsing followed by an allowlist sanitizer. Rewrite relative `.md` links to app routes, preserve anchors and external links, and rewrite relative images/other assets to their copied docs asset path. Render Mermaid fences through Mermaid initialized on the selected content page. Render OpenAPI YAML in a readable code/reference view. External SVG/vector images remain viewable; add a React-owned accessible diagram dialog for `.diagram-figure` content or preserve equivalent behavior.

## Demo integration and trust boundaries
Keep `docs/javascripts/demo-explorer.js` as the rendering/data adapter for now. The React Demo page mounts the existing static explorer markup and initializes the legacy script only after the mount exists. Add a teardown or idempotent initializer if route revisits can otherwise register duplicate listeners/timers. Keep all artifact data untrusted; existing normalizers and `textContent` DOM writes stay authoritative. Public demo paths are resolved from the configured Pages base path, not the current nested URL. Do not weaken fixture-path, digest, evidence, run-identity, repository URL, or visibility validation.

## Visual system
Architecture uses a calm light reading canvas, editorial type scale, compact nav rail, ample line length, crisp diagrams, and focused table/code treatments. Demo uses a dark ink shell, clear execution-state colors, compact monospace metadata, card-based evidence and scenario browsing, and visible stage progression. Both share brand, type, spacing, focus ring, corner and accent rules. Add subtle CSS transitions/entrance effects, never imply that decorative animation represents a live workflow; honor reduced motion.

## Alternatives
- Keep MkDocs and restyle: rejected by the user's direct feedback; insufficiently distinct from documentation software.
- Next.js/SSR: unnecessary because GitHub Pages is static and the current workflows generate data before deploy.
- Replace demo logic while migrating: high risk and unrelated to the UI outcome; retain and host it behind a stable adapter, then consider a later dedicated React migration.

## Verification
Test route resolution, Markdown link/asset resolution, static build output and 404 fallback; add a browser-level smoke test at desktop and narrow widths if the repository environment supports Playwright. Retain demo explorer and diagram viewer unit suites, and test that initialization/teardown is safe on route changes. Run the existing OpenAPI and Python workflow gates as CI does, plus Vite build and generated-output checks.
