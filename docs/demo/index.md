---
hide:
  - toc
---

<div id="demo-explorer" class="demo-page">

<header class="demo-hero">
  <span class="demo-eyebrow">GITHUB ACTIONS · RUNNABLE PROOF OF CONCEPT</span>
  <h1>Follow a decision from rule to evidence.</h1>
  <p>Launch the workflow in GitHub, then use this page to explore what the PoC actually does: pinned inputs, code analysis, source observations, evidence, a bounded mock assessment, validation, and the audit record.</p>
  <div class="demo-actions">
    <a id="demo-open-analysis" class="md-button md-button--primary" href="#">Run PoC analysis</a>
    <a id="demo-open-evaluation" class="md-button" href="#">Run corpus evaluation</a>
  </div>
</header>

<div class="demo-trust-note" role="note">
  <strong>Two kinds of data appear here.</strong>
  <span>The walkthrough is regenerated from a checked-in synthetic Go fixture with the offline mock provider. Run history comes from GitHub Actions. On a private repository with internal-only Pages explicitly enabled, this page also shows a bounded projection of real PoC ledger rows. It never publishes prompts, credentials, or provider payloads; source excerpts are redacted and linked to their original artifact hashes.</span>
</div>

<section class="demo-section" aria-labelledby="demo-walkthrough-heading">
  <div class="demo-section-heading">
    <div><span class="demo-eyebrow">SYNTHETIC WALKTHROUGH</span><h2 id="demo-walkthrough-heading">Move through the analysis</h2></div>
    <span id="demo-sample-label" class="demo-pill">Loading fixture run…</span>
  </div>
  <p id="demo-sample-meta" class="demo-muted"></p>
  <p id="demo-sample-status" class="demo-warning" aria-live="polite"></p>
  <div class="demo-pipeline-layout">
    <nav class="demo-stage-rail" aria-label="PoC analysis stages">
      <ol id="demo-stages" class="demo-stages"></ol>
      <div class="demo-controls">
        <button id="demo-previous" class="md-button" type="button" disabled>Previous</button>
        <button id="demo-play" class="md-button" type="button" aria-pressed="false">Play stages</button>
        <button id="demo-pause" class="md-button" type="button" disabled>Pause</button>
        <button id="demo-next" class="md-button md-button--primary" type="button" disabled>Next</button>
      </div>
      <span id="demo-stage-announcer" class="demo-sr-only" aria-live="polite"></span>
    </nav>
    <article class="demo-stage-panel" aria-live="polite">
      <div class="demo-stage-panel__top"><span id="demo-stage-number" class="demo-stage-number"></span><span id="demo-stage-status" class="demo-status">loading</span></div>
      <h3 id="demo-stage-title">Loading walkthrough</h3>
      <p id="demo-stage-description">The site build creates a deterministic fixture run.</p>
      <p id="demo-stage-counts" class="demo-stage-counts"></p>
      <div class="demo-stage-track" aria-hidden="true"><span></span></div>
      <p class="demo-muted">Each stage corresponds to events in the PoC's <code>run_events.csv</code>. The complete synthetic example outputs are explored below.</p>
    </article>
  </div>
</section>

<section class="demo-section" aria-labelledby="demo-output-heading">
  <div class="demo-section-heading">
    <div><span class="demo-eyebrow">EXAMPLE OUTPUTS</span><h2 id="demo-output-heading">Inspect the evidence and decision</h2></div>
    <span id="demo-final-outcome" class="demo-outcome">Loading</span>
  </div>
  <article class="demo-finding-card">
    <div><span class="demo-eyebrow">VALIDATED MOCK FINDING</span><p id="demo-final-summary">Waiting for the synthetic run output.</p></div>
    <div class="demo-score-card"><strong id="demo-score">—</strong><span id="demo-score-band">Evidence support</span><small id="demo-score-meaning">Not a calibrated probability.</small></div>
  </article>
  <details class="demo-disclosure" open>
    <summary>Confidence dimensions and guardrails</summary>
    <p><span id="demo-score-version"></span> · The score measures evidence support. It is not a probability that a deviation exists.</p>
    <div id="demo-confidence-components" class="demo-component-grid"></div>
  </details>
  <details class="demo-disclosure" open>
    <summary>Evidence with source-version references</summary>
    <p>Source SHA-256 identifies the full checked-in fixture file. Excerpt SHA-256 identifies the excerpt displayed here.</p>
    <div id="demo-evidence-list" class="demo-evidence-grid"></div>
  </details>
  <div class="demo-output-columns">
    <details class="demo-disclosure" open>
      <summary>Language-neutral observations</summary>
      <div id="demo-observation-list" class="demo-observation-list"></div>
    </details>
    <details class="demo-disclosure" open>
      <summary>Collection coverage and gaps</summary>
      <ul id="demo-coverage-list" class="demo-coverage-list"></ul>
    </details>
  </div>
  <details class="demo-disclosure">
    <summary>Input snapshot identity</summary>
    <p>This digest binds the selected fixture artifacts and paths for the example run:</p>
    <code id="demo-input-hash" class="demo-hash"></code>
  </details>
</section>

<section class="demo-section" aria-labelledby="demo-history-heading">
  <div class="demo-section-heading">
    <div><span class="demo-eyebrow">ACTUAL GITHUB ACTIONS</span><h2 id="demo-history-heading">Browse previous workflow runs</h2></div>
    <button id="demo-reload-history" class="md-button" type="button">Refresh run history</button>
  </div>
  <p id="demo-history-status" class="demo-muted" role="status">Loading workflow run history…</p>
  <div id="demo-run-list" class="demo-run-grid"></div>
  <div id="demo-run-jobs" class="demo-run-jobs" aria-live="polite"></div>
  <div id="demo-real-run-record" class="demo-run-record"></div>
  <p class="demo-muted">Selecting a run shows job and step statuses. In internal-data mode, the matching audit record expands to show real stages, finding, evidence, observations, confidence, and coverage. Use “Open workflow run and artifacts” for the original bundle.</p>
</section>

<section class="demo-section demo-run-guide" aria-labelledby="demo-launch-heading">
  <div class="demo-section-heading"><div><span class="demo-eyebrow">RUN IT YOURSELF</span><h2 id="demo-launch-heading">Launch and inspect a workflow</h2></div></div>
  <ol>
    <li>Open <a id="demo-guide-analysis" href="#">PoC Analysis</a> and choose <strong>Run workflow</strong>. The defaults use the checked-in Go fixture and the offline mock provider.</li>
    <li>For infrastructure or other declarative YAML/JSON inputs, choose <code>none</code> as the language and set <code>config_source</code>. Unsupported formats are reported as incomplete coverage, not as compliance.</li>
    <li>Open the run's job summary and download the <code>adr-deviation-poc-…</code> artifact. Inspect <code>report.md</code>, <code>confidence.json</code>, <code>evidence.json</code>, <code>observations.json</code>, and the CSV tables.</li>
    <li>Use <a id="demo-guide-evaluation" href="#">ADR Deviation Labeled Evaluation</a> to run deterministic regression cases and the 50-ADR extraction/coverage audit.</li>
  </ol>
  <p><strong>Scope boundary:</strong> these are repository-hosted demonstrators, not the proposed Step Functions/AWS production service. The synthetic corpus is not independently adjudicated; mock evaluation does not measure model quality. Anthropic mode requires repository secrets and provider-data approval.</p>
</section>

</div>
