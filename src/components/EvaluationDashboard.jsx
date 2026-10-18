import React, { useState } from 'react';
import { ArrowRight, ArrowUpRight, CheckCircle2, CircleHelp, ClipboardCheck, GitCompareArrows, GitPullRequest, LockKeyhole, Play, ShieldCheck } from 'lucide-react';

const tracks = {
  regression: {
    eyebrow: 'DEVELOPMENT REGRESSION',
    title: 'Does a code change break a known case?',
    description: 'The deterministic mock suite checks the current detector against the same 20 synthetic async-boundary cases. It is useful for finding regressions in the rules and evidence contract, not for estimating production accuracy.',
    facts: [
      ['20', 'synthetic labeled cases'],
      ['3-way', 'deviation · aligned · ambiguous'],
      ['By family', 'behavior-level breakdowns'],
    ],
    actions: [
      { label: 'Run mock evaluation', href: 'https://github.com/tyler-beach/Platform/actions/workflows/poc-evaluation.yml', primary: true },
      { label: 'Read evaluation protocol', href: 'https://github.com/tyler-beach/Platform/blob/main/docs/EVALUATION_AND_FEEDBACK.md' },
    ],
    status: 'Development corpus · synthetic labels · not independently adjudicated',
  },
  coverage: {
    eyebrow: 'ADR EVIDENCE COVERAGE',
    title: 'Can the evidence collector find the facts?',
    description: 'A separate 50-ADR fixture audit checks source integrity and deterministic collection of declared configuration facts. Cases that require runtime state must remain inconclusive when the required telemetry is absent.',
    facts: [
      ['50', 'synthetic ADR fixtures'],
      ['35', 'declared-configuration facts'],
      ['15', 'runtime-state evidence gaps'],
    ],
    actions: [
      { label: 'Run corpus evaluation', href: 'https://github.com/tyler-beach/Platform/actions/workflows/poc-evaluation.yml', primary: true },
      { label: 'Inspect corpus audit code', href: 'https://github.com/tyler-beach/Platform/tree/main/.poc/evaluation' },
    ],
    status: 'Evidence collection audit · does not measure natural-language interpretation quality',
  },
  holdout: {
    eyebrow: 'QUARANTINED HOLDOUT',
    title: 'Keep the independent check independent.',
    description: 'Four provisional cases are hash-locked and intentionally unlabeled. They are not an accuracy benchmark yet. Independent reviewers must adjudicate them through an approved process before a separate evaluation can score them.',
    facts: [
      ['4', 'provisional cases'],
      ['Locked', 'content fingerprint checked in CI'],
      ['Pending', 'independent adjudication required'],
    ],
    actions: [
      { label: 'Inspect holdout policy', href: 'https://github.com/tyler-beach/Platform/blob/main/.poc/evaluation/holdout-lock.json', primary: true },
      { label: 'Read evaluation boundaries', href: 'https://github.com/tyler-beach/Platform/blob/main/docs/EVALUATION.md' },
    ],
    status: 'Quarantined · excluded from tuning and routine regression scoring',
  },
};

const reviewStages = [
  { title: 'Select a review sample', detail: 'Record the frame fingerprint, random seed, selected units, inclusion probabilities, design weights, and sampling method. Keep probability sampling separate from risk triage.' },
  { title: 'Open or reconcile the GitHub Issue', detail: 'Issues are the reviewer-facing intake and discussion surface. They contain stable identifiers and evidence references, not copied source excerpts or secrets.' },
  { title: 'Record a disposition', detail: 'Append a reviewer event with a supported disposition, rationale, and evidence references. Comments alone are not the authoritative ledger.' },
  { title: 'Get independent adjudication', detail: 'A different person resolves disagreements and approves the outcome. A reviewer’s initial disposition is not ground truth.' },
  { title: 'Export a candidate fixture', detail: 'Export only eligible, provenance-complete, split-tagged candidates. The exporter must not edit the baseline corpus or locked holdout.' },
  { title: 'Compare before promotion', detail: 'Run the full regression suite and inspect metric changes, per-family changes, corpus fingerprints, and configuration. Promotion remains a separate human decision.' },
];

export default function EvaluationDashboard() {
  const [track, setTrack] = useState('regression');
  const [stageIndex, setStageIndex] = useState(0);
  const current = tracks[track];
  const stage = reviewStages[stageIndex];
  return <div className="evaluation-page">
    <header className="evaluation-hero">
      <span className="evaluation-kicker"><ShieldCheck size={14} /> PATHFINDER / EVALUATION</span>
      <h1>Measure what changed.<br/><em>Keep the evidence.</em></h1>
      <p>Run the offline checks, compare the candidate with the base revision, and trace reviewer feedback without turning an unverified opinion into a new baseline.</p>
      <div className="evaluation-hero__actions">
        <a className="evaluation-action evaluation-action--primary" href="https://github.com/tyler-beach/Platform/actions/workflows/poc-evaluation.yml" target="_blank" rel="noreferrer"><Play size={15} /> Run evaluation workflow <ArrowUpRight size={14}/></a>
        <a className="evaluation-action" href="https://github.com/tyler-beach/Platform/issues?q=is%3Aissue+label%3Apathfinder-review" target="_blank" rel="noreferrer"><GitPullRequest size={15}/> Review issues <ArrowUpRight size={14}/></a>
      </div>
      <div className="evaluation-trust-note"><LockKeyhole size={15}/><span>Offline mock by default · no paid model calls · holdout stays quarantined</span></div>
    </header>

    <section className="evaluation-section" aria-labelledby="evaluation-track-title">
      <div className="evaluation-section__heading"><div><span className="evaluation-kicker">01 / CHOOSE A TRACK</span><h2 id="evaluation-track-title">Three checks, three different questions</h2></div><p>Do not combine these numbers into one score. They measure different things.</p></div>
      <div className="evaluation-track-tabs" role="tablist" aria-label="Evaluation track">
        <button type="button" role="tab" aria-selected={track === 'regression'} onClick={() => setTrack('regression')}>Detector regression</button>
        <button type="button" role="tab" aria-selected={track === 'coverage'} onClick={() => setTrack('coverage')}>Evidence coverage</button>
        <button type="button" role="tab" aria-selected={track === 'holdout'} onClick={() => setTrack('holdout')}>Locked holdout</button>
      </div>
      <article className="evaluation-track-panel" role="tabpanel">
        <div className="evaluation-track-panel__intro"><span className="evaluation-kicker">{current.eyebrow}</span><h3>{current.title}</h3><p>{current.description}</p></div>
        <div className="evaluation-facts">{current.facts.map(([value, label]) => <div className="evaluation-fact" key={value + label}><strong>{value}</strong><span>{label}</span></div>)}</div>
        <div className="evaluation-track-panel__footer"><span><CircleHelp size={14}/>{current.status}</span><div>{current.actions.map(action => <a key={action.label} className={action.primary ? 'is-primary' : ''} href={action.href} target="_blank" rel="noreferrer">{action.label}<ArrowUpRight size={13}/></a>)}</div></div>
      </article>
    </section>

    <section className="evaluation-section" aria-labelledby="evaluation-compare-title">
      <div className="evaluation-section__heading"><div><span className="evaluation-kicker">02 / REGRESSION COMPARISON</span><h2 id="evaluation-compare-title">Compare the candidate to its base</h2></div><p>Pull requests run the deterministic mock evaluation on both revisions and attach a machine-readable comparison report.</p></div>
      <div className="evaluation-compare-grid">
        <article><GitCompareArrows size={19}/><h3>Like-for-like when possible</h3><p>Each report carries the dataset fingerprint and analysis configuration. If either changes, the comparison marks the results as not like-for-like instead of hiding the difference.</p></article>
        <article><ClipboardCheck size={19}/><h3>Review the deltas</h3><p>Inspect overall metrics, counts, and scenario-family changes. CI does not invent a release threshold; the synthetic corpus is too narrow to justify one.</p></article>
      </div>
      <p className="evaluation-note">The comparison is a regression aid, not a quality certification. Green CI means the checks passed—not that the detector is production-ready.</p>
    </section>

    <section className="evaluation-section" aria-labelledby="review-loop-title">
      <div className="evaluation-section__heading"><div><span className="evaluation-kicker">03 / HUMAN FEEDBACK LOOP</span><h2 id="review-loop-title">From sampled case to candidate regression</h2></div><p>Choose a stage to see what must be recorded before the work can move forward.</p></div>
      <div className="evaluation-review-loop">
        <nav className="evaluation-review-loop__steps" aria-label="Review lifecycle">
          {reviewStages.map((item, index) => <button type="button" key={item.title} aria-current={index === stageIndex ? 'step' : undefined} className={index === stageIndex ? 'is-active' : ''} onClick={() => setStageIndex(index)}><span>{String(index + 1).padStart(2, '0')}</span><strong>{item.title}</strong><ArrowRight size={14}/></button>)}
        </nav>
        <article className="evaluation-review-loop__detail" aria-live="polite"><span className="evaluation-kicker">STAGE {String(stageIndex + 1).padStart(2, '0')} / 06</span><h3>{stage.title}</h3><p>{stage.detail}</p><div className="evaluation-review-loop__guardrail"><CheckCircle2 size={16}/><span>{stageIndex < 3 ? 'Keep the source revision and evidence references attached.' : 'Never automatically modify the labeled baseline or holdout.'}</span></div><div className="evaluation-review-loop__controls"><button type="button" disabled={stageIndex === 0} onClick={() => setStageIndex(value => value - 1)}>Previous</button><button type="button" onClick={() => setStageIndex(value => (value + 1) % reviewStages.length)}>{stageIndex === reviewStages.length - 1 ? 'Start again' : 'Next stage'}<ArrowRight size={14}/></button></div></article>
      </div>
      <div className="evaluation-feedback-actions"><div><strong>Ready to review a real sample?</strong><p>Start from the controlled workflow so the sample manifest and provenance are recorded.</p></div><a href="https://github.com/tyler-beach/Platform/actions/workflows/pathfinder-scope-review-intake.yml" target="_blank" rel="noreferrer">Open review intake workflow <ArrowUpRight size={14}/></a></div>
    </section>

    <footer className="evaluation-boundaries"><ShieldCheck size={18}/><div><strong>What these checks do not claim</strong><p>The development labels are synthetic and unadjudicated. The holdout is pending independent review. Evidence support is not a calibrated probability. Human review remains responsible for disposition and promotion.</p></div></footer>
  </div>;
}
