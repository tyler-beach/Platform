import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Braces, CheckCircle2, ChevronRight, CircleHelp, Clock3, ExternalLink, FileCode2, GitBranch, Pause, Play, RefreshCw, ShieldCheck, Workflow } from 'lucide-react';
import { BASE_URL } from '../content.js';

const repository = document.querySelector('meta[name="adr-repository"]')?.content || 'tyler-beach/Platform';

export default function DemoExplorer() {
  const supportingDetailsRef = useRef(null);
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
        <div className="demo-kicker"><span className="demo-kicker__pulse" /> INTERACTIVE WALKTHROUGH <span className="demo-kicker__divider" /> EXAMPLE DATA</div>
        <h1>From decision to <em>evidence.</em></h1>
        <p>Start with a short example. See how a written decision is checked against implementation evidence, what the evidence shows, and what still needs a closer look.</p>
        <div className="demo-launch-actions"><button type="button" className="demo-launch-button demo-launch-button--primary" onClick={() => { document.getElementById("requirement-lab-title")?.scrollIntoView({ behavior: "smooth", block: "start" }); document.getElementById("journey-watch-button")?.click(); }}><Play size={14} fill="currentColor" /> Watch an investigation <ArrowRight size={13} /></button><button type="button" className="demo-launch-button demo-launch-button--explore" onClick={() => { if (supportingDetailsRef.current) supportingDetailsRef.current.open = true; document.getElementById("demo-gallery-heading")?.scrollIntoView({ behavior: "smooth", block: "start" }); }}>Explore the evidence <ArrowRight size={13} /></button></div>
      </div>
      <div className="demo-hero__visual" aria-hidden="true"><div className="demo-ring demo-ring--outer" /><div className="demo-ring demo-ring--inner" /><div className="demo-hero-node demo-hero-node--top"><GitBranch size={16} /></div><div className="demo-hero-node demo-hero-node--left"><ShieldCheck size={16} /></div><div className="demo-hero-node demo-hero-node--right"><CheckCircle2 size={16} /></div><div className="demo-hero-core"><Workflow size={25} /><span>INVESTIGATION</span><small>5 stages</small></div><i className="demo-orbit-dot demo-orbit-dot--one" /><i className="demo-orbit-dot demo-orbit-dot--two" /></div>
      <div className="demo-hero__footer"><span><span className="demo-hero__status-dot" /> GUIDED EXAMPLE</span><span>Move from a written rule to a reviewable finding</span></div>
    </section>

    <div className="demo-trust-banner"><div className="demo-trust-banner__icon"><ShieldCheck size={19} /></div><div><strong>This walkthrough uses example data</strong><p>The guided scenarios are synthetic and do not inspect a live system. You can open the separate PoC workflow and inspect its run artifacts when you want to see the underlying implementation.</p></div><Link to="/architecture/SECURITY">How trust is handled <ArrowRight size={14} /></Link></div>

    <RequirementLab />

    <section className="technical-trace" aria-labelledby="technical-trace-title">
      <div className="technical-trace__heading">
        <div><span className="demo-label">IMPLEMENTATION TRACE · SYNTHETIC EXAMPLE</span><h2 id="technical-trace-title">Inspect the data path, not just the finding</h2></div>
        <p>The scanner and evidence contract are checked into this repository. This is representative output from the current PoC contract, not a live repository scan.</p>
      </div>
      <div className="technical-trace__grid">
        <article className="technical-trace__panel">
          <div className="technical-trace__panel-title"><Braces size={17} /><div><strong>01 / AST observation</strong><small>Language-specific AST / SSA · static call graph</small></div></div>
          <p className="technical-trace__explain">Collectors are language-specific: Python uses <code>ast</code> plus scope/import/type-hint indexes; Go uses <code>go/packages</code>, <code>go/types</code>, SSA and CHA; TypeScript/JavaScript use a dedicated call-graph collector. A normalizer emits source-bound observations. This is not one universal Tree-sitter pass.</p>
          <pre aria-label="Example normalized code observation JSON"><code>{JSON.stringify({
  schema_version: "source-observation-v1",
  observation_id: "obs:<sha256-of-canonical-observation>",
  predicate: "code.call_edge",
  subject: {
    id: "py:src/session.py:42:validate_session",
    kind: "function",
    name: "service.session.validate_session"
  },
  value: {
    target: "service.providers.assess",
    call_expression: "provider.assess(request)",
    edge_id: "edge:<collector-edge-id>",
    reachable_from_entry: true,
    dispatch_kind: "static"
  },
  source_ref: {
    artifact_id: "artifact:<run-bound-id>",
    version: "git:<immutable-revision>",
    sha256: "<64-character-source-digest>",
    path: "src/session.py",
    locator: { kind: "line", start: 42, end: 42 }
  },
  collector: {
    name: "language-callgraph",
    version: "callgraph-observations-v1",
    language: "python",
    resolver: "Python AST + scope/import/type-hint/constructor index",
    run_id: "run-example-0042"
  },
  resolution: {
    status: "resolved",
    source_status: "resolved_static",
    basis: "scope_import_index"
  },
  evidence_class: "static_code_observation"
}, null, 2)}</code></pre>
          <ul className="technical-trace__notes"><li>PoC observations use one-based line locators plus immutable artifact version and SHA-256; the Python collector also records symbol line ranges.</li><li>Resolution varies by language and resolver. “Resolved” is static-analysis status, not runtime proof.</li><li>Unresolved / approximate edges and collector diagnostics remain explicit; coverage gaps must not be interpreted as absence.</li></ul>
          <a href={`https://github.com/${repository}/blob/main/.poc/analyzers/python_callgraph.py`} target="_blank" rel="noreferrer">Read the Python AST collector <ArrowUpRight size={13} /></a>
        </article>
        <article className="technical-trace__panel">
          <div className="technical-trace__panel-title"><ShieldCheck size={17} /><div><strong>02 / Evidence item</strong><small>Immutable source reference · claim relation</small></div></div>
          <p className="technical-trace__explain">This is the proposed internal EvidenceItem contract in docs/contracts/EVIDENCE.md. It is distinct from the PoC’s persisted source-observation envelope shown next to it. Excerpts are review data, not general-purpose logs; model output cannot invent evidence IDs or locations.</p>
          <pre aria-label="Example evidence item JSON"><code>{JSON.stringify({
  evidenceId: "ev-001",
  jobId: "job-example-0042",
  artifactId: "repo:service/session.py",
  artifactVersionId: "git:<full-immutable-revision>",
  artifactKind: "source_file",
  contentSha256: "<sha256-of-canonical-source>",
  path: "src/session.py",
  startLine: 42,
  endLine: 42,
  symbolOrSection: "validate_session",
  locatorPrecision: "EXACT",
  excerptSha256: "<sha256-of-exact-excerpt>",
  relationToClaim: "CONTRADICTS",
  retrievalMethod: "path_symbol_v1",
  selectionRationale: "Contains the configured absolute lifetime check",
  sourceIntegrity: "VERIFIED",
  collectedAt: "<UTC timestamp from collection>"
}, null, 2)}</code></pre>
          <ul className="technical-trace__notes"><li>Artifact version, source digest, and inclusive line range must agree.</li><li>Each factual claim must cite evidence in the same immutable job package.</li><li>Missing, stale, contradictory, or weak evidence downgrades the result to potential or inconclusive.</li></ul>
          <a href={`https://github.com/${repository}/blob/main/docs/contracts/EVIDENCE.md`} target="_blank" rel="noreferrer">Read the evidence contract <ArrowUpRight size={13} /></a>
        </article>
        <article className="technical-trace__panel technical-trace__panel--wide">
          <div className="technical-trace__panel-title"><Clock3 size={17} /><div><strong>03 / Append-only run event</strong><small>PoC audit log · run_events.csv</small></div></div>
          <p className="technical-trace__explain">The PoC records stage transitions separately from evidence and findings. The event row is a timeline pointer; structured details stay in <code>details_json</code>, while source references and model transactions live in their own tables.</p>
          <pre aria-label="Example run event JSON"><code>{JSON.stringify({
  event_id: "evt-0007",
  run_id: "run-example-0042",
  timestamp: "2026-10-17T12:00:04Z",
  stage: "evidence_collection",
  event_type: "collection_completed",
  status: "completed",
  details_json: {
    inspected_files: 12,
    emitted_observations: 7,
    unresolved_edges: 2,
    coverage_complete: false
  }
}, null, 2)}</code></pre>
          <div className="technical-trace__tables"><div><strong>Related audit tables</strong><p><code>artifacts</code> · immutable input hashes and versions</p><p><code>symbols</code> / <code>call_edges</code> · normalized graph facts and resolution state</p><p><code>evidence</code> / <code>observations</code> · claim-linked source records and predicates</p></div><div><strong>Assessment and governance</strong><p><code>collection_reports</code> · coverage, unsupported files, failed collectors, gaps</p><p><code>findings</code> / <code>assessment_evidence_links</code> · outcome, limitations, claim relationships, validation</p><p><code>llm_transactions</code> / <code>confidence_assessments</code> · prompt digest, token counts, versioned scoring inputs</p></div></div>
          <a href={`https://github.com/${repository}/blob/main/.poc/store.py`} target="_blank" rel="noreferrer">Read the canonical PoC CSV schemas <ArrowUpRight size={13} /></a>
        </article>
      </div>
      <div className="technical-trace__boundary"><strong>Boundary:</strong> AST facts are deterministic syntax observations. Semantic applicability, runtime behavior, and whether a deviation is confirmed require additional evidence and human review. The JSON above is illustrative; hashes and IDs are placeholders, not verifiable artifact identities.</div>
    </section>

    <details ref={supportingDetailsRef} id="demo-supporting-details" className="demo-supporting-details"><summary>Go deeper: scenarios, PoC runs, and evidence <span>Technical details for closer inspection</span></summary><div className="demo-supporting-details__body">
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
      <div className="demo-section__inner demo-run-guide"><div className="demo-workflow-links"><a id="demo-open-analysis" href="#">Run PoC analysis <ArrowUpRight size={13}/></a><a id="demo-open-evaluation" href="#">Run corpus evaluation <ArrowUpRight size={13}/></a><a id="demo-open-functional" href="#">Run Tree-sitter demo <ArrowUpRight size={13}/></a></div><ol><li>Open <a id="demo-guide-analysis" href="#">PoC Analysis</a> and choose <strong>Run workflow</strong>. Defaults use the checked-in Go fixture and offline mock provider.</li><li>For infrastructure YAML/JSON, choose <code>none</code> as the language and set <code>config_source</code>. Unsupported formats are incomplete coverage, not compliance.</li><li>Download the <code>adr-deviation-poc-…</code> artifact and inspect reports, evidence, observations, confidence, and CSV tables.</li><li>Use <a id="demo-guide-evaluation" href="#">the labeled evaluation</a> for regression cases and the 50-ADR coverage audit.</li><li>Use <a id="demo-guide-functional" href="#">Functional Analysis Demo</a> for the Tree-sitter and document-analysis workflow. Validated fixture artifacts can appear in the scenario library for a bounded recovery window.</li></ol><div className="demo-scope-note"><CircleHelp size={16} /><p>This is a repository-hosted demonstrator, not the proposed production service. The synthetic corpus is not independently adjudicated; mock evaluation does not measure model quality. Provider mode requires repository secrets and data approval.</p></div></div>
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
      { id: 'E-01', title: 'Availability objective', detail: 'Service contract · minimum two available replicas', source: 'service-availability-policy.md · lines 12–18', location: 'service-availability-policy.md:12–18 · illustrative', excerpt: 'At least 2 replicas must remain available during voluntary disruption.', supports: 'States the minimum number of replicas the service must keep available.', limits: 'Does not show the current replica count or how the disruption budget is configured.' },
      { id: 'E-02', title: 'Workload topology', detail: 'Desired replicas: 3', source: 'workload specification · replicas field', location: 'workload.yaml · spec.replicas · illustrative', excerpt: 'replicas: 3', supports: 'Shows the desired replica count in this example.', limits: 'Does not prove that three replicas are healthy or available at runtime.' },
      { id: 'E-03', title: 'Effective disruption budget', detail: 'Maximum unavailable: 2', source: 'disruption-budget.yaml · spec.maxUnavailable', location: 'disruption-budget.yaml · spec.maxUnavailable · illustrative', excerpt: 'maxUnavailable: 2', supports: 'Shows the configured allowance for voluntary disruption in this example.', limits: 'The workload selector and same-environment identity still need validation.' },
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
      { id: 'E-01', title: 'Session lifetime requirement', detail: 'Maximum absolute lifetime: 60 minutes', source: 'ADR-PLATFORM-002 · Decision', location: 'ADR-PLATFORM-002 · Decision · illustrative excerpt', excerpt: 'The maximum permitted session lifetime is 60 minutes from session establishment.', supports: 'Sets the absolute session lifetime limit.', limits: 'The decision alone does not show how the running system enforces expiry.' },
      { id: 'E-02', title: 'Effective session setting', detail: 'Absolute lifetime: 90 minutes', source: 'identity/session.yaml · session.absolute_lifetime', location: 'identity/session.yaml · session.absolute_lifetime · illustrative', excerpt: 'absolute_lifetime: 90m', supports: 'Shows a configured maximum 30 minutes above the decision.', limits: 'A setting does not prove which environment is running or how refresh is enforced.' },
      { id: 'E-03', title: 'Renewal semantics', detail: 'Refresh and server-side acceptance checks are not supplied', source: 'refresh flow · evidence gap', location: 'No source excerpt supplied for this example', excerpt: 'Evidence not provided: refresh-token behavior and server-side session acceptance.', supports: 'Names the missing checks needed before confirming the finding.', limits: 'Cannot establish whether the refresh flow is safe or unsafe without its implementation.' },
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
  const [activeKey, setActiveKey] = useState('ttl');
  const [activeStage, setActiveStage] = useState(0);
  const [activeEvidence, setActiveEvidence] = useState('E-01');
  const [review, setReview] = useState({});
  const [isPlaying, setIsPlaying] = useState(false);
  const tabRefs = useRef({});
  const example = requirementExamples[activeKey];
  const stage = example.stages[activeStage];
  const selectedEvidence = example.evidence.find(item => item.id === activeEvidence) || example.evidence[0];

  useEffect(() => {
    if (!isPlaying) return undefined;
    if (activeStage >= example.stages.length - 1) {
      setIsPlaying(false);
      return undefined;
    }
    const timer = window.setTimeout(() => setActiveStage(activeStage + 1), 7000);
    return () => window.clearTimeout(timer);
  }, [isPlaying, activeStage, example.stages.length]);

  function chooseExample(key) {
    setIsPlaying(false);
    setActiveKey(key);
    setActiveStage(0);
    setActiveEvidence('E-01');
  }
  function goToStage(index) {
    setIsPlaying(false);
    setActiveStage(Math.max(0, Math.min(example.stages.length - 1, index)));
  }
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

  const stepNames = ['Decision', 'Scope', 'Evidence', 'Assessment', 'Review'];
  const progress = ((activeStage + 1) / example.stages.length) * 100;

  return <section className="requirement-lab journey-lab" aria-labelledby="requirement-lab-title">
    <header className="requirement-lab__topbar">
      <div className="requirement-lab__brand"><span className="requirement-lab__brand-mark"><Workflow size={18}/></span><span><strong>ADR / FIELDNOTES</strong><small>GUIDED INVESTIGATION · ABOUT 60 SECONDS</small></span></div>
      <span className="requirement-lab__mode"><i/> SYNTHETIC ENVIRONMENT</span>
    </header>

    <div className="journey-intro">
      <div className="journey-intro__copy">
        <span className="demo-label">FROM DECISION TO EVIDENCE</span>
        <h2 id="requirement-lab-title">A decision is only useful<br/>if the system <em>follows it.</em></h2>
        <p>Watch one architectural rule move through scope, evidence, and review. No security background required.</p>
      </div>
      <div className="journey-intro__actions">
        <button id="journey-watch-button" type="button" className="journey-primary" onClick={() => { if (isPlaying) { setIsPlaying(false); return; } if (activeStage === example.stages.length - 1) setActiveStage(0); setIsPlaying(true); }}>{isPlaying ? <><Pause size={15}/> Pause walkthrough</> : <><Play size={15} fill="currentColor"/> {activeStage === example.stages.length - 1 ? 'Replay walkthrough' : 'Watch an investigation'}</>} <ArrowRight size={15}/></button>
        <span>Five steps · inspect the sources · you make the call</span>
      </div>
    </div>

    <nav className="journey-scenarios" role="tablist" aria-label="Choose an example investigation">
      {Object.values(requirementExamples).map((item, index) => <button key={item.key} ref={node => { tabRefs.current[item.key] = node; }} id={`adr-tab-${item.key}`} tabIndex={activeKey === item.key ? 0 : -1} type="button" role="tab" aria-controls="journey-panel" aria-selected={activeKey === item.key} className={activeKey === item.key ? 'is-active' : ''} onKeyDown={event => handleTabKeyDown(event, index)} onClick={() => chooseExample(item.key)}><span className="journey-scenarios__number">0{index + 1}</span><span><strong>{item.key === 'ttl' ? 'Session lifetime' : 'Pod availability'}</strong><small>{item.key === 'ttl' ? 'IDENTITY SECURITY' : 'KUBERNETES · RESILIENCE'}</small></span><ArrowUpRight size={15}/></button>)}
    </nav>

    <div className="journey-workspace" id="journey-panel" role="tabpanel" aria-labelledby={`adr-tab-${activeKey}`}>
      <aside className="journey-rail" aria-label="Investigation progress">
        <div className="journey-rail__heading"><span className="demo-label">INVESTIGATION</span><strong>{String(activeStage + 1).padStart(2, '0')} <small>/ 05</small></strong></div>
        <div className="journey-rail__track" aria-hidden="true"><span style={{height: progress + '%'}}/></div>
        {example.stages.map((item, index) => <button key={item[0]} type="button" className={'journey-rail__step' + (index === activeStage ? ' is-active' : '') + (index < activeStage ? ' is-complete' : '')} aria-current={index === activeStage ? 'step' : undefined} onClick={() => goToStage(index)}><span>{index < activeStage ? <CheckCircle2 size={15}/> : String(index + 1).padStart(2, '0')}</span><span><strong>{stepNames[index]}</strong><small>{['The rule', 'Applicability', 'Source facts', 'Compare values', 'Human decision'][index]}</small></span><ChevronRight size={14}/></button>)}
        <div className="journey-rail__note"><ShieldCheck size={15}/><span>Evidence first.<br/>Human decision.</span></div>
      </aside>

      <div className="journey-scene" aria-live="polite">
        <div className="journey-scene__top"><span className="demo-label">STEP {String(activeStage + 1).padStart(2, '0')} · {stepNames[activeStage].toUpperCase()}</span><span className="journey-scene__state"><i/>{isPlaying ? 'PLAYING' : activeStage === 4 ? 'READY FOR REVIEW' : 'GUIDED MODE'}</span></div>
        {activeStage === 0 && <div className="journey-scene__content journey-scene__content--decision">
          <span className="journey-overline">THE ARCHITECTURE DECISION</span>
          <h3>{example.title}</h3>
          <blockquote>{example.requirement}</blockquote>
          <div className="journey-explain"><span className="journey-explain__icon"><CircleHelp size={17}/></span><p><strong>In plain English</strong>{activeKey === 'ttl' ? 'A session must end within one hour. Clicking around or refreshing a token must not keep the same session alive longer.' : 'When a service has three replicas and needs two available, its disruption policy must not allow too many to be taken offline at once.'}</p></div>
          <p className="journey-scene__hint">First, the system needs to know which services and components this rule applies to.</p>
        </div>}
        {activeStage === 1 && <div className="journey-scene__content">
          <span className="journey-overline">STEP 02 · FIND WHAT THE RULE COVERS</span>
          <h3>Which parts of the system are in scope?</h3>
          <p className="journey-lede">{example.stages[0][1]}</p>
          <div className="journey-map">
            <div className="journey-map__node journey-map__node--decision"><FileCode2 size={17}/><span><strong>Approved decision</strong><small>{activeKey === 'ttl' ? 'Maximum 60 minutes' : 'At least 2 replicas available'}</small></span><CheckCircle2 size={16}/></div>
            <div className="journey-map__connector"><span/></div>
            <div className="journey-map__node"><GitBranch size={17}/><span><strong>{activeKey === 'ttl' ? 'Authentication & session services' : 'Workload & disruption policy'}</strong><small>{activeKey === 'ttl' ? 'Session creation · refresh · validation' : 'Replica count · selector · availability budget'}</small></span><span className="journey-tag">SCOPE</span></div>
            <div className="journey-map__caption">Scope is resolved before the system compares settings. A matching file name alone is not enough.</div>
          </div>
        </div>}
        {activeStage === 2 && <div className="journey-scene__content">
          <span className="journey-overline">STEP 03 · COLLECT SOURCE-LINKED EVIDENCE</span>
          <h3>What does the implementation actually say?</h3>
          <p className="journey-lede">The demo compares the decision with observed configuration and identifies what still needs verification.</p>
          <div className="journey-evidence-list">{example.evidence.map((item, index) => <button key={item.id} type="button" aria-pressed={activeEvidence === item.id} className={'journey-evidence-row' + (activeEvidence === item.id ? ' is-active' : '')} onClick={() => { setIsPlaying(false); setActiveEvidence(item.id); }}><span className="journey-evidence-row__id">{item.id}</span><span className="journey-evidence-row__copy"><strong>{item.title}</strong><small>{item.detail}</small><code>{item.source}</code></span><span className="journey-evidence-row__mark">{index === 0 ? 'RULE' : index === 1 ? 'OBSERVED' : 'CHECK'}</span></button>)}</div>
          <div className="journey-selected-source"><FileCode2 size={17}/><div className="journey-selected-source__body"><span className="demo-label">SYNTHETIC REF · EVIDENCE INSPECTOR · {selectedEvidence.id}</span><strong>{selectedEvidence.title}</strong><p>{selectedEvidence.detail}</p><small>{selectedEvidence.location}</small><pre className="journey-selected-source__excerpt">{selectedEvidence.excerpt}</pre><div className="journey-selected-source__checks"><p><strong>What this supports</strong>{selectedEvidence.supports}</p><p><strong>What it does not prove</strong>{selectedEvidence.limits}</p></div></div></div>
        </div>}
        {activeStage === 3 && <div className="journey-scene__content">
          <span className="journey-overline">STEP 04 · COMPARE REQUIREMENT WITH EVIDENCE</span>
          <h3>The values do not line up.</h3>
          <p className="journey-lede">The observed setting conflicts with the stated limit. That is a signal to investigate—not an automatic enforcement action.</p>
          <div className="journey-comparison">
            <div className="journey-comparison__cell"><span>REQUIRED</span><strong>{activeKey === 'ttl' ? '60 min' : '2 available'}</strong><small>{activeKey === 'ttl' ? 'Absolute session lifetime' : 'Minimum available replicas'}</small></div>
            <div className="journey-comparison__operator">≠</div>
            <div className="journey-comparison__cell journey-comparison__cell--observed"><span>OBSERVED</span><strong>{activeKey === 'ttl' ? '90 min' : '2 unavailable'}</strong><small>{activeKey === 'ttl' ? 'Configured maximum' : 'Permitted disruption'}</small></div>
          </div>
          <div className="journey-assessment-note"><ShieldCheck size={17}/><p><strong>What the evidence supports</strong>{activeKey === 'ttl' ? 'The configured maximum is 30 minutes above the decision. Refresh and server-side acceptance behavior still need checking.' : 'The observed budget may permit more disruption than the availability objective allows. Selector and environment identity must be verified.'}</p></div>
        </div>}
        {activeStage === 4 && <div className="journey-scene__content">
          <span className="journey-overline">STEP 05 · HUMAN REVIEW</span>
          <div className="journey-outcome"><span className="journey-outcome__icon"><ShieldCheck size={21}/></span><div><span className="journey-overline">CURRENT ASSESSMENT</span><h3>{example.outcome}</h3></div><span className="journey-outcome__badge">REVIEW REQUIRED</span></div>
          <p className="journey-lede">{activeKey === 'ttl' ? 'The configuration conflicts with the 60-minute rule. Before confirming a deviation, verify token refresh behavior and that the server rejects sessions past the absolute boundary.' : 'The budget may conflict with the approved availability objective. Before confirming a deviation, verify that its selector targets the intended workload and that all values come from the same environment.'}</p>
          <div className="journey-review-gap"><CircleHelp size={17}/><div><strong>Still needs evidence</strong><p>{example.gaps}</p></div></div>
          <div className="journey-review-actions"><span>YOUR REVIEW</span>{['confirm', 'dismiss', 'inconclusive'].map(value => <button key={value} type="button" className={review[activeKey] === value ? 'is-active' : ''} aria-pressed={review[activeKey] === value} onClick={() => setReview(previous => ({...previous, [activeKey]: value}))}>{value === 'confirm' ? 'Confirm finding' : value === 'dismiss' ? 'Dismiss' : 'Need more evidence'}</button>)}</div>
          {review[activeKey] && <p className="journey-review-result" role="status">Your local choice: {review[activeKey]}. This example does not change a system or send data anywhere.</p>}
        </div>}
        <footer className="journey-controls">
          <div className="journey-controls__left"><span>{activeStage + 1} of {example.stages.length}</span><span className="journey-controls__dots" aria-label={`Step ${activeStage + 1} of 5`}>{example.stages.map((item, index) => <i key={item[0]} className={index === activeStage ? 'is-active' : index < activeStage ? 'is-complete' : ''}/>)}</span></div>
          <div className="journey-controls__buttons"><button type="button" className="journey-secondary" disabled={activeStage === 0} onClick={() => goToStage(activeStage - 1)}>Back</button><button type="button" className="journey-secondary" onClick={() => { if (isPlaying) setIsPlaying(false); else { if (activeStage === example.stages.length - 1) setActiveStage(0); setIsPlaying(true); } }}>{isPlaying ? <><Pause size={14}/> Pause</> : <><Play size={14}/> {activeStage === example.stages.length - 1 ? 'Replay' : 'Resume'}</>}</button><button type="button" className="journey-next" onClick={() => { if (activeStage === example.stages.length - 1) { setIsPlaying(false); setActiveStage(0); } else goToStage(activeStage + 1); }}>{activeStage === example.stages.length - 1 ? 'Start again' : 'Next step'} <ArrowRight size={15}/></button></div>
        </footer>
      </div>
    </div>
    <div className="journey-footnote"><span><ShieldCheck size={14}/> Example data only · no live systems checked</span><span>Fixed example · findings still need human review</span></div>
  </section>;
}
