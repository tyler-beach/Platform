import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, CheckCircle2, ChevronRight, CircleHelp, Clock3, ExternalLink, FileCode2, GitBranch, Play, RefreshCw, ShieldCheck, Workflow } from 'lucide-react';
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
        <div className="demo-launch-actions">{workflows.map(([id, label]) => <a key={id} id={id} className="demo-launch-button" href="#"><Play size={14} fill="currentColor" /> {label} <ArrowUpRight size={13} /></a>)}<a className="demo-launch-button demo-launch-button--explore" href="#requirement-lab-title">Explore an ADR <ArrowRight size={13} /></a></div>
      </div>
      <div className="demo-hero__visual" aria-hidden="true"><div className="demo-ring demo-ring--outer" /><div className="demo-ring demo-ring--inner" /><div className="demo-hero-node demo-hero-node--top"><GitBranch size={16} /></div><div className="demo-hero-node demo-hero-node--left"><ShieldCheck size={16} /></div><div className="demo-hero-node demo-hero-node--right"><CheckCircle2 size={16} /></div><div className="demo-hero-core"><Workflow size={25} /><span>ANALYSIS</span><small>4 stages</small></div><i className="demo-orbit-dot demo-orbit-dot--one" /><i className="demo-orbit-dot demo-orbit-dot--two" /></div>
      <div className="demo-hero__footer"><span><span className="demo-hero__status-dot" /> POC WORKFLOW</span><span>Design baseline + runnable GitHub Actions implementation</span></div>
    </section>

    <div className="demo-trust-banner"><div className="demo-trust-banner__icon"><ShieldCheck size={19} /></div><div><strong>Synthetic examples, source-bound evidence</strong><p>The scenario library and walkthrough use checked-in fixtures and an offline mock provider. Recent live artifact text appears only after run identity, digests, input hashes, evidence, and synthetic fixture paths are verified. This is not a calibrated model-quality claim.</p></div><Link to="/architecture/SECURITY">Trust boundaries <ArrowRight size={14} /></Link></div>

    <RequirementLab />

    <details className="demo-supporting-details"><summary>Explore the underlying demo artifacts <span>Scenario library · Pipeline walkthrough · Evidence outputs</span></summary><div className="demo-supporting-details__body">
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
    </div></details>
  </div>;
}

function LayersIcon() { return <span className="layers-icon"><Workflow size={18} /></span>; }

function DemoSection({ id, kicker, title, icon, badge, badgeId, action, children }) {
  return <section className="demo-section" aria-labelledby={id}><div className="demo-section-heading"><div className="demo-section-heading__title"><span className="demo-section-heading__icon">{icon}</span><div><span className="demo-label">{kicker}</span><h2 id={id}>{title}</h2></div></div><div className="demo-section-heading__action">{badgeId ? <span id={badgeId} className="demo-badge">{badge}</span> : badge && <span className="demo-badge">{badge}</span>}{action}</div></div>{children}</section>;
}



const requirementExamples = {
  pdb: {
    key: 'pdb', title: 'Preserve availability during voluntary disruption', eyebrow: 'PLATFORM POLICY · KUBERNETES WORKLOADS',
    requirement: 'Availability-sensitive workloads MUST maintain an effective disruption budget consistent with their approved availability objective and replica topology.',
    context: 'The budget must select the intended workload. Resource presence alone is not proof of compliance.',
    expected: 'The effective budget constrains voluntary disruptions to the service’s approved availability objective.',
    observation: 'A workload has three replicas and requires at least two available, but the observed budget permits two to be voluntarily unavailable.',
    outcome: 'Potential deviation',
    evidence: [
      { id: 'E-01', title: 'Availability objective', detail: 'Service contract · minimum two available replicas', source: 'service-availability-policy.md · lines 12–18' },
      { id: 'E-02', title: 'Workload topology', detail: 'Desired replicas: 3', source: 'workload specification · replicas field' },
      { id: 'E-03', title: 'Effective disruption budget', detail: 'Maximum unavailable: 2', source: 'disruption budget · selector and availability constraint' },
    ],
    gaps: 'Confirm the budget selector resolves to the intended workload and that the replica count is from the same environment and source version.',
    stages: [
      ['Scope', 'Resolve workload ownership and availability classification.'],
      ['Requirements', 'Extract the minimum availability invariant.'],
      ['Evidence', 'Bind workload, objective, and effective budget to source versions.'],
      ['Assessment', 'Compare the configured disruption allowance with the objective.'],
      ['Validation', 'Check selector identity, freshness, and evidence completeness.'],
    ],
  },
  ttl: {
    key: 'ttl', title: 'Limit authenticated session lifetime to 60 minutes', eyebrow: 'IDENTITY POLICY · AUTHENTICATED SESSIONS',
    requirement: 'The maximum permitted session lifetime MUST be 60 minutes from session establishment. Activity MUST NOT extend the existing session beyond this absolute maximum.',
    context: 'The rule applies regardless of language, framework, cookie, token format, or session storage. A timeout setting alone is insufficient if another component renews the session.',
    expected: 'The session is rejected at or before 60 minutes; renewal requires a new authentication event or explicitly approved reauthentication.',
    observation: 'The session configuration permits a 90-minute absolute lifetime.',
    outcome: 'Potential deviation',
    evidence: [
      { id: 'E-01', title: 'Session lifetime requirement', detail: 'Maximum absolute lifetime: 60 minutes', source: 'ADR-PLATFORM-002 · Decision' },
      { id: 'E-02', title: 'Effective session setting', detail: 'Absolute lifetime: 90 minutes', source: 'identity configuration · session lifetime field' },
      { id: 'E-03', title: 'Renewal semantics', detail: 'Verify refresh and server-side acceptance behavior', source: 'refresh flow and session validation path' },
    ],
    gaps: 'Inspect refresh-token behavior and server-side session acceptance. A 60-minute token claim does not prove the system rejects a refreshed or otherwise accepted session after the absolute boundary.',
    stages: [
      ['Scope', 'Identify the authentication components and session types covered.'],
      ['Requirements', 'Extract the 60-minute absolute lifetime invariant.'],
      ['Evidence', 'Inspect configured expiration, token claims, and renewal behavior.'],
      ['Assessment', 'Compare the effective maximum with the requirement.'],
      ['Validation', 'Verify expiry rejection and that activity cannot extend the same session indefinitely.'],
    ],
  },
};

function RequirementLab() {
  const [activeKey, setActiveKey] = useState('pdb');
  const [activeStage, setActiveStage] = useState(2);
  const [activeEvidence, setActiveEvidence] = useState('E-02');
  const [review, setReview] = useState({});
  const tabRefs = useRef({});
  const example = requirementExamples[activeKey];
  const stage = example.stages[activeStage];
  const selectedEvidence = example.evidence.find(item => item.id === activeEvidence) || example.evidence[0];
  function chooseExample(key) { setActiveKey(key); setActiveStage(0); setActiveEvidence('E-01'); }
  function handleTabKeyDown(event, index) {
    const keys = Object.keys(requirementExamples);
    let nextIndex = index;
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % keys.length;
    else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + keys.length) % keys.length;
    else if (event.key === 'Home') nextIndex = 0;
    else if (event.key === 'End') nextIndex = keys.length - 1;
    else return;
    event.preventDefault();
    const nextKey = keys[nextIndex];
    chooseExample(nextKey);
    tabRefs.current[nextKey]?.focus();
  }

  return <section className="requirement-lab" aria-labelledby="requirement-lab-title">
    <header className="requirement-lab__topbar">
      <div className="requirement-lab__brand"><span className="requirement-lab__brand-mark"><Workflow size={18}/></span><span><strong>ADR / FIELDNOTES</strong><small>DECISION VALIDATION WORKSPACE</small></span></div>
      <span className="requirement-lab__mode"><i/> SYNTHETIC ENVIRONMENT</span>
    </header>
    <div className="requirement-lab__intro">
      <div><span className="demo-label">DECISION → IMPLEMENTATION</span><h2 id="requirement-lab-title">See where the system<br/><em>drifts from the decision.</em></h2><p>Choose a policy. Follow the evidence. Inspect the gap. This is the core ADR investigation loop—not a language-specific code demo.</p></div>
      <nav className="requirement-lab__switcher" role="tablist" aria-label="Select an architectural decision">
        {Object.values(requirementExamples).map((item, index) => <button key={item.key} ref={node => { tabRefs.current[item.key] = node; }} id={`adr-tab-${item.key}`} tabIndex={activeKey === item.key ? 0 : -1} type="button" role="tab" aria-controls="requirement-lab-panel" aria-selected={activeKey === item.key} className={activeKey === item.key ? 'is-active' : ''} onKeyDown={event => handleTabKeyDown(event, index)} onClick={() => chooseExample(item.key)}><span className="requirement-lab__switcher-index">{item.key === 'pdb' ? '01' : '02'}</span><span><strong>{item.key === 'pdb' ? 'Pod disruption budget' : 'Session lifetime'}</strong><small>{item.key === 'pdb' ? 'AVAILABILITY' : 'IDENTITY SECURITY'}</small></span><ArrowUpRight size={14}/></button>)}
      </nav>
    </div>
    <div className="requirement-lab__surface" id="requirement-lab-panel" role="tabpanel" aria-labelledby={`adr-tab-${activeKey}`} tabIndex={0}>
      <div className="requirement-lab__surface-head"><div><span className="demo-label">{example.eyebrow}</span><h3>{example.title}</h3></div><span className="requirement-lab__scope"><span/> POLICY SCOPE · DEFINED</span></div>
      <div className="requirement-lab__rule"><span className="requirement-lab__rule-tag">DECISION</span><p>{example.requirement}</p><button type="button" className="requirement-lab__rule-link" onClick={() => {setActiveStage(1);setActiveEvidence('E-01');}}>Inspect requirement <ArrowRight size={14}/></button></div>
      <div className="requirement-lab__journey">
        <div className="requirement-lab__journey-line" aria-hidden="true"><span style={{width: ((activeStage / (example.stages.length - 1)) * 100) + '%'}}/></div>
        {example.stages.map((item, index) => <button key={item[0]} type="button" className={'requirement-lab__journey-step ' + (activeStage === index ? 'is-active' : '') + (index < activeStage ? ' is-complete' : '')} aria-current={activeStage === index ? 'step' : undefined} onClick={() => setActiveStage(index)}><span className="requirement-lab__journey-number">{index < activeStage ? <CheckCircle2 size={15}/> : String(index + 1).padStart(2, '0')}</span><strong>{item[0]}</strong></button>)}
      </div>
      <div className="requirement-lab__stage-focus" aria-live="polite"><div className="requirement-lab__stage-copy"><span className="demo-label">STEP {String(activeStage + 1).padStart(2, '0')} / 0{example.stages.length}</span><h4>{stage[0]}<span>.</span></h4><p>{stage[1]}</p></div><div className="requirement-lab__stage-controls"><button type="button" aria-label="Previous stage" disabled={activeStage === 0} onClick={() => setActiveStage(value => Math.max(0, value - 1))}><ArrowRight size={15} className="requirement-lab__back-arrow"/></button><button type="button" aria-label="Next stage" disabled={activeStage === example.stages.length - 1} onClick={() => setActiveStage(value => Math.min(example.stages.length - 1, value + 1))}><span>Next step</span><ArrowRight size={15}/></button></div></div>
      <div className="requirement-lab__signal-grid">
        <article className="requirement-lab__signal requirement-lab__signal--observation"><div className="requirement-lab__signal-head"><span className="requirement-lab__signal-icon"><GitBranch size={15}/></span><span className="demo-label">OBSERVED STATE</span><span className="requirement-lab__signal-index">02</span></div><p>{example.observation}</p><button type="button" onClick={() => {setActiveEvidence('E-02');setActiveStage(2);}}>Inspect source evidence <ArrowRight size={13}/></button></article>
        <article className="requirement-lab__signal requirement-lab__signal--finding"><div className="requirement-lab__signal-head"><span className="requirement-lab__signal-icon"><ShieldCheck size={15}/></span><span className="demo-label">CANDIDATE FINDING</span><span className="requirement-lab__signal-index">03</span></div><p><strong>{example.outcome}</strong> — verify the workload/session scope, source freshness, and counterevidence before deciding.</p><span className="requirement-lab__finding-note">NOT AN ENFORCEMENT ACTION</span></article>
      </div>
      <div className="requirement-lab__evidence-strip">
        <div className="requirement-lab__evidence-title"><span className="demo-label">EVIDENCE TRAIL</span><strong>What supports the finding?</strong><small>{example.evidence.length} illustrative references</small></div>
        <div className="requirement-lab__evidence-select">{example.evidence.map(item => <button key={item.id} type="button" className={activeEvidence === item.id ? 'is-active' : ''} aria-pressed={activeEvidence === item.id} onClick={() => setActiveEvidence(item.id)}><span>{item.id}</span><strong>{item.title}</strong><ArrowUpRight size={14}/></button>)}</div>
        <div className="requirement-lab__source-view" aria-live="polite"><FileCode2 size={17}/><div><span className="demo-label">SELECTED SOURCE</span><strong>{selectedEvidence.title}</strong><p>{selectedEvidence.detail} <span>·</span> {selectedEvidence.source}</p></div><span className="requirement-lab__pinned">SYNTHETIC REF</span></div>
      </div>
      <footer className="requirement-lab__review-bar"><div className="requirement-lab__gap-inline"><CircleHelp size={16}/><span><strong>Open evidence question</strong><small>{example.gaps}</small></span></div><div className="requirement-lab__review-actions"><span>REVIEW</span>{['confirm', 'dismiss', 'inconclusive'].map(value => <button key={value} type="button" className={review[activeKey] === value ? 'is-active' : ''} aria-pressed={review[activeKey] === value} onClick={() => setReview(previous => ({...previous, [activeKey]: value}))}>{value === 'confirm' ? 'Confirm' : value === 'dismiss' ? 'Dismiss' : 'Inconclusive'}</button>)}</div>{review[activeKey] && <p className="requirement-lab__review-state" role="status">Local demo choice: {review[activeKey]}. Nothing was written to production.</p>}</footer>
    </div>
    <div className="requirement-lab__footnote"><span><ShieldCheck size={14}/> Synthetic fixture · no live infrastructure queried</span><span>Assessment is evidence-led, reviewable, and reversible.</span></div>
  </section>;
}
