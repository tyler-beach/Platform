import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, CheckCircle2, CircleHelp, Clock3, ExternalLink, GitBranch, Play, RefreshCw, ShieldCheck, Workflow } from 'lucide-react';
import { BASE_URL } from '../content.js';

const repository = document.querySelector('meta[name="adr-repository"]')?.content || 'tyler-beach/Platform';

const workflows = [
  ['demo-open-analysis', 'Run PoC analysis', 'poc-analysis.yml'],
  ['demo-open-evaluation', 'Run corpus evaluation', 'poc-evaluation.yml'],
  ['demo-open-functional', 'Run Tree-sitter demo', 'functional-analysis-demo.yml'],
];

export default function DemoExplorer() {
  useEffect(() => {
    let mounted = true;
    import('../../docs/javascripts/demo-explorer.js').then(() => {
      if (mounted) globalThis.ADRDemoLifecycle?.init();
    });
    return () => { mounted = false; globalThis.ADRDemoLifecycle?.destroy(); };
  }, []);

  return <div className="demo-experience" id="demo-explorer">
    <section className="demo-hero">
      <div className="demo-hero__content">
        <div className="demo-kicker"><span className="demo-kicker__pulse" /> LIVE WORKFLOW EXPLORER <span className="demo-kicker__divider" /> SYNTHETIC FIRST</div>
        <h1>From decision to <em>evidence.</em></h1>
        <p>Explore how the proof of concept pins its inputs, gathers source observations, validates evidence, and records a reviewable outcome.</p>
        <div className="demo-launch-actions">{workflows.map(([id, label]) => <a key={id} id={id} className="demo-launch-button" href="#"><Play size={14} fill="currentColor" /> {label} <ArrowUpRight size={13} /></a>)}</div>
      </div>
      <div className="demo-hero__visual" aria-hidden="true"><div className="demo-ring demo-ring--outer" /><div className="demo-ring demo-ring--inner" /><div className="demo-hero-node demo-hero-node--top"><GitBranch size={16} /></div><div className="demo-hero-node demo-hero-node--left"><ShieldCheck size={16} /></div><div className="demo-hero-node demo-hero-node--right"><CheckCircle2 size={16} /></div><div className="demo-hero-core"><Workflow size={25} /><span>ANALYSIS</span><small>4 stages</small></div><i className="demo-orbit-dot demo-orbit-dot--one" /><i className="demo-orbit-dot demo-orbit-dot--two" /></div>
      <div className="demo-hero__footer"><span><span className="demo-hero__status-dot" /> POC WORKFLOW</span><span>Design baseline + runnable GitHub Actions implementation</span></div>
    </section>

    <div className="demo-trust-banner"><div className="demo-trust-banner__icon"><ShieldCheck size={19} /></div><div><strong>Synthetic examples, source-bound evidence</strong><p>The scenario library and walkthrough use checked-in fixtures and an offline mock provider. Recent live artifact text appears only after run identity, digests, input hashes, evidence, and synthetic fixture paths are verified. This is not a calibrated model-quality claim.</p></div><Link to="/architecture/SECURITY">Trust boundaries <ArrowRight size={14} /></Link></div>

    <DemoSection id="demo-gallery-heading" kicker="SCENARIO LIBRARY" title="Compare spec, code, and change" icon={<LayersIcon />} badge="9 CURATED CASES">
      <div className="demo-section__inner demo-gallery-surface">
        <p id="demo-gallery-status" className="demo-muted" role="status" aria-live="polite">Loading the offline synthetic scenario catalog…</p>
        <nav id="demo-gallery-list" className="demo-gallery-choices" aria-label="Synthetic comparison scenarios" />
        <article className="demo-gallery-detail" aria-live="polite">
          <div className="demo-gallery-detail__heading"><div><span className="demo-label">SELECTED SYNTHETIC RUN</span><h3 id="demo-gallery-selected-title">Loading scenario</h3><p id="demo-gallery-selected-meta" className="demo-muted" /></div><span id="demo-gallery-selected-outcome" className="demo-outcome">Loading</span></div>
          <p id="demo-gallery-run-link" /><p id="demo-gallery-rationale" />
          <div className="demo-subheading"><div><span className="demo-label">INPUT SNAPSHOT</span><h4>Exact sources used</h4></div><p>Hashes bind each source to the selected fixture bytes.</p></div>
          <div id="demo-gallery-inputs" className="demo-gallery-inputs" />
          <div className="demo-gallery-output-grid"><details className="demo-disclosure" open><summary>Requirements extracted</summary><ul id="demo-gallery-requirements" className="demo-gallery-stage-list" /></details><details className="demo-disclosure" open><summary>Code observations</summary><ul id="demo-gallery-observations" className="demo-gallery-stage-list" /></details></div>
          <div className="demo-gallery-output-grid"><details className="demo-disclosure" open><summary>Workflow stages</summary><ol id="demo-gallery-stages" className="demo-gallery-stage-list" /></details><details className="demo-disclosure"><summary>Validated checks</summary><ul id="demo-gallery-checks" className="demo-gallery-stage-list" /></details></div>
          <details className="demo-disclosure"><summary>Evidence references</summary><div id="demo-gallery-evidence" className="demo-evidence-grid" /></details>
        </article>
      </div>
    </DemoSection>

    <DemoSection id="demo-walkthrough-heading" kicker="SYNTHETIC WALKTHROUGH" title="Follow the analysis stages" icon={<Workflow />} badgeId="demo-sample-label" badge="Loading fixture run…">
      <div className="demo-section__inner">
        <p id="demo-sample-meta" className="demo-muted" /><p id="demo-sample-status" className="demo-warning" aria-live="polite" />
        <div className="demo-pipeline-layout"><nav className="demo-stage-rail" aria-label="PoC analysis stages"><ol id="demo-stages" className="demo-stages" /><div className="demo-controls"><button id="demo-previous" className="demo-button" type="button" disabled>Previous</button><button id="demo-play" className="demo-button" type="button" aria-pressed="false">Play stages</button><button id="demo-pause" className="demo-button" type="button" disabled>Pause</button><button id="demo-next" className="demo-button demo-button--accent" type="button" disabled>Next <ArrowRight size={14} /></button></div><span id="demo-stage-announcer" className="demo-sr-only" aria-live="polite" /></nav>
          <article className="demo-stage-panel" aria-live="polite"><div className="demo-stage-panel__top"><span id="demo-stage-number" className="demo-stage-number" /><span id="demo-stage-status" className="demo-status">loading</span></div><h3 id="demo-stage-title">Loading walkthrough</h3><p id="demo-stage-description">The build creates a deterministic fixture run.</p><p id="demo-stage-counts" className="demo-stage-counts" /><div className="demo-stage-track" aria-hidden="true"><span /></div><p className="demo-muted">Each stage corresponds to events in the PoC’s <code>run_events.csv</code>. The full example outputs follow below.</p></article>
        </div>
      </div>
    </DemoSection>

    <DemoSection id="demo-output-heading" kicker="EXAMPLE OUTPUTS" title="Inspect the evidence and result" icon={<ShieldCheck />} badgeId="demo-final-outcome" badge="Loading">
      <div className="demo-section__inner">
        <article className="demo-finding-card"><div><span className="demo-label">VALIDATED MOCK FINDING</span><p id="demo-final-summary">Waiting for the synthetic run output.</p></div><div className="demo-score-card"><strong id="demo-score">—</strong><span id="demo-score-band">Evidence support</span><small id="demo-score-meaning">Not a calibrated probability.</small></div></article>
        <details className="demo-disclosure" open><summary>Confidence dimensions and guardrails</summary><p><span id="demo-score-version" /> · The score measures evidence support. It is not the probability that a deviation exists.</p><div id="demo-confidence-components" className="demo-component-grid" /></details>
        <details className="demo-disclosure" open><summary>Evidence with source-version references</summary><p>Source SHA-256 identifies the full checked-in fixture. Excerpt SHA-256 identifies the text shown here.</p><div id="demo-evidence-list" className="demo-evidence-grid" /></details>
        <div className="demo-output-columns"><details className="demo-disclosure" open><summary>Language-neutral observations</summary><div id="demo-observation-list" className="demo-observation-list" /></details><details className="demo-disclosure" open><summary>Collection coverage and gaps</summary><ul id="demo-coverage-list" className="demo-coverage-list" /></details></div>
        <details className="demo-disclosure"><summary>Input snapshot identity</summary><p>This digest binds the selected fixture artifacts and paths for the example run:</p><code id="demo-input-hash" className="demo-hash" /></details>
      </div>
    </DemoSection>

    <DemoSection id="demo-history-heading" kicker="GITHUB ACTIONS" title="Browse workflow history" icon={<Clock3 />} action={<button id="demo-reload-history" className="demo-button" type="button"><RefreshCw size={14} /> Refresh runs</button>}>
      <div className="demo-section__inner"><p id="demo-history-status" className="demo-muted" role="status">Loading workflow run history…</p><div id="demo-run-list" className="demo-run-grid" /><div id="demo-run-jobs" className="demo-run-jobs" aria-live="polite" /><div id="demo-real-run-record" className="demo-run-record" /><p className="demo-muted demo-footnote">Selecting a run shows job and step states. Internal audit records include stages, provenance, evidence, and checks. Functional Analysis confidence is marked unavailable. Open the original workflow for downloadable artifacts.</p></div>
    </DemoSection>

    <DemoSection id="demo-launch-heading" kicker="RUN IT YOURSELF" title="Launch a workflow" icon={<Play size={17} />}>
      <div className="demo-section__inner demo-run-guide"><ol><li>Open <a id="demo-guide-analysis" href="#">PoC Analysis</a> and choose <strong>Run workflow</strong>. Defaults use the checked-in Go fixture and offline mock provider.</li><li>For infrastructure YAML/JSON, choose <code>none</code> as the language and set <code>config_source</code>. Unsupported formats are incomplete coverage, not compliance.</li><li>Download the <code>adr-deviation-poc-…</code> artifact and inspect reports, evidence, observations, confidence, and CSV tables.</li><li>Use <a id="demo-guide-evaluation" href="#">the labeled evaluation</a> for regression cases and the 50-ADR coverage audit.</li><li>Use <a id="demo-guide-functional" href="#">Functional Analysis Demo</a> for the Tree-sitter and document-analysis workflow. Validated fixture artifacts can appear in the scenario library for a bounded recovery window.</li></ol><div className="demo-scope-note"><CircleHelp size={16} /><p>This is a repository-hosted demonstrator, not the proposed production service. The synthetic corpus is not independently adjudicated; mock evaluation does not measure model quality. Provider mode requires repository secrets and data approval.</p></div></div>
    </DemoSection>
    <div className="demo-endnote"><span><CheckCircle2 size={16} /> Evidence and provenance stay inspectable at every stage.</span><a href={`https://github.com/${repository}/actions`} target="_blank" rel="noreferrer">Open all Actions <ExternalLink size={13} /></a></div>
  </div>;
}

function LayersIcon() { return <span className="layers-icon"><Workflow size={18} /></span>; }

function DemoSection({ id, kicker, title, icon, badge, badgeId, action, children }) {
  return <section className="demo-section" aria-labelledby={id}><div className="demo-section-heading"><div className="demo-section-heading__title"><span className="demo-section-heading__icon">{icon}</span><div><span className="demo-label">{kicker}</span><h2 id={id}>{title}</h2></div></div><div className="demo-section-heading__action">{badgeId ? <span id={badgeId} className="demo-badge">{badge}</span> : badge && <span className="demo-badge">{badge}</span>}{action}</div></div>{children}</section>;
}
