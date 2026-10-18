import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertCircle, ArrowDownToLine, ArrowUpRight, CheckCircle2, ChevronDown,
  CircleDashed, Clock3, ExternalLink, FileJson2, FileText, GitBranch, LoaderCircle,
  RefreshCw, Search, ShieldAlert, Workflow, XCircle,
} from 'lucide-react';

const OWNER_REPO = document.querySelector('meta[name="adr-repository"]')?.content || 'tyler-beach/Platform';
const API = 'https://api.github.com';
const STATES = {
  success: { label: 'Succeeded', icon: CheckCircle2, tone: 'success' },
  failure: { label: 'Failed', icon: XCircle, tone: 'failure' },
  cancelled: { label: 'Cancelled', icon: XCircle, tone: 'muted' },
  skipped: { label: 'Skipped', icon: CircleDashed, tone: 'muted' },
  in_progress: { label: 'In progress', icon: LoaderCircle, tone: 'running' },
  queued: { label: 'Queued', icon: CircleDashed, tone: 'muted' },
  waiting: { label: 'Waiting', icon: CircleDashed, tone: 'muted' },
  action_required: { label: 'Action required', icon: ShieldAlert, tone: 'failure' },
};
const toneFor = (value) => STATES[value]?.tone || 'muted';
const prettyDate = (value) => value ? new Date(value).toLocaleString() : 'Not recorded';
const duration = (start, end) => {
  if (!start) return '—';
  const ms = Math.max(0, new Date(end || Date.now()) - new Date(start));
  if (ms < 1000) return '<1s';
  if (ms < 60000) return `${Math.round(ms / 1000)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
};
const titleForStep = (step) => String(step.name || 'Unnamed step').replace(/^\d+\s*[·.)-]\s*/, '');
const safeJson = (value) => JSON.stringify(value, null, 2);

// Parse GitHub's ZIP response locally; log contents remain in the browser and are never sent elsewhere.
async function readZipEntries(buffer) {
  const view = new DataView(buffer);
  const decoder = new TextDecoder();
  let end = -1;
  for (let i = Math.max(0, buffer.byteLength - 65557); i <= buffer.byteLength - 22; i += 1) { if (view.getUint32(i, true) === 0x06054b50) end = i; }
  if (end < 0) throw new Error('The downloaded file is not a readable ZIP archive.');
  const count = view.getUint16(end + 10, true);
  let cursor = view.getUint32(end + 16, true);
  const entries = [];
  for (let i = 0; i < count; i += 1) {
    if (view.getUint32(cursor, true) !== 0x02014b50) break;
    const method = view.getUint16(cursor + 10, true);
    const size = view.getUint32(cursor + 20, true);
    const nameLength = view.getUint16(cursor + 28, true);
    const extraLength = view.getUint16(cursor + 30, true);
    const commentLength = view.getUint16(cursor + 32, true);
    const localOffset = view.getUint32(cursor + 42, true);
    const name = decoder.decode(new Uint8Array(buffer, cursor + 46, nameLength));
    const localNameLength = view.getUint16(localOffset + 26, true);
    const localExtraLength = view.getUint16(localOffset + 28, true);
    const start = localOffset + 30 + localNameLength + localExtraLength;
    const bytes = new Uint8Array(buffer, start, size);
    let content;
    if (method === 0) content = bytes.slice();
    else if (method === 8 && typeof DecompressionStream !== 'undefined') {
      const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
      content = new Uint8Array(await new Response(stream).arrayBuffer());
    } else throw new Error('This browser cannot decompress this ZIP format. Download the artifact from GitHub instead.');
    entries.push({ name, bytes: content, text: decoder.decode(content) });
    cursor += 46 + nameLength + extraLength + commentLength;
  }
  return entries.filter((entry) => !entry.name.endsWith('/'));
}

function Status({ value }) {
  const state = STATES[value] || { label: value || 'Unknown', icon: CircleDashed, tone: 'muted' };
  const Icon = state.icon;
  return <span className={`run-status run-status--${state.tone}`}><Icon size={14} />{state.label}</span>;
}

export default function RunExplorer() {
  const [runs, setRuns] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [selectedAttempt, setSelectedAttempt] = useState(1);
  const [compareEnabled, setCompareEnabled] = useState(false);
  const [compareId, setCompareId] = useState('');
  const [compareAttempt, setCompareAttempt] = useState(1);
  const [compareDetails, setCompareDetails] = useState({ jobs: [], artifacts: [], loading: false, error: '' });
  const [jobs, setJobs] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [selectedStepKey, setSelectedStepKey] = useState('');
  const [tab, setTab] = useState('summary');
  const [query, setQuery] = useState('');
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [error, setError] = useState('');
  const [detailsError, setDetailsError] = useState('');
  const [jobLogs, setJobLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsError, setLogsError] = useState('');
  const [artifactContents, setArtifactContents] = useState({});
  const [artifactLoading, setArtifactLoading] = useState('');
  const [artifactErrors, setArtifactErrors] = useState({});
  const [lastUpdated, setLastUpdated] = useState('');

  const selectedRun = runs.find((run) => String(run.id) === selectedId) || null;
  const comparisonRun = runs.find((run) => String(run.id) === compareId) || null;
  const allSteps = useMemo(() => jobs.flatMap((job) => (job.steps || []).map((step, index) => ({
    ...step, jobName: job.name, jobId: job.id, jobConclusion: job.conclusion,
    key: `${job.id}:${step.number ?? index}`, jobUrl: job.html_url,
  }))), [jobs]);
  const selectedStep = allSteps.find((step) => step.key === selectedStepKey) || allSteps[0] || null;
  const matchingStepLogs = useMemo(() => {
    if (!selectedStep) return [];
    return jobLogs.filter((entry) => {
      const base = entry.name.split('/').pop() || entry.name;
      const numberMatch = base.match(/^(\d+)[_ .-]/);
      return numberMatch && Number(numberMatch[1]) === Number(selectedStep.number);
    });
  }, [jobLogs, selectedStep]);
  const visibleStepLogs = matchingStepLogs.length ? matchingStepLogs : jobLogs;
  const filteredRuns = runs.filter((run) => {
    const label = [run.name, run.display_title, run.head_branch, run.head_sha, run.id].join(' ').toLowerCase();
    return label.includes(query.toLowerCase());
  });
  const completedSteps = allSteps.filter((step) => step.status === 'completed').length;
  const failedSteps = allSteps.filter((step) => step.conclusion === 'failure').length;
  const compareSteps = useMemo(() => {
    if (!compareEnabled || !comparisonRun) return [];
    const normalize = (value) => String(value || '').toLowerCase().replace(/\s+/g, ' ').trim();
    const primaryJobs = new Map(jobs.map((job) => [normalize(job.name), job]));
    const otherJobs = new Map(compareDetails.jobs.map((job) => [normalize(job.name), job]));
    const rows = [];
    for (const jobName of new Set([...primaryJobs.keys(), ...otherJobs.keys()])) {
      const primary = primaryJobs.get(jobName), other = otherJobs.get(jobName);
      const primarySteps = new Map((primary?.steps || []).map((step) => [normalize(step.name), step]));
      const otherSteps = new Map((other?.steps || []).map((step) => [normalize(step.name), step]));
      for (const stepName of new Set([...primarySteps.keys(), ...otherSteps.keys()])) {
        const left = primarySteps.get(stepName), right = otherSteps.get(stepName);
        const leftStatus = left?.conclusion || left?.status || 'missing';
        const rightStatus = right?.conclusion || right?.status || 'missing';
        const leftMs = left?.started_at ? Math.max(0, new Date(left.completed_at || Date.now()) - new Date(left.started_at)) : null;
        const rightMs = right?.started_at ? Math.max(0, new Date(right.completed_at || Date.now()) - new Date(right.started_at)) : null;
        let change = 'Unchanged';
        if (!left) change = 'Added in selected run';
        else if (!right) change = 'Missing in selected run';
        else if (leftStatus !== rightStatus) change = 'Outcome changed';
        else if (leftMs !== null && rightMs !== null && Math.abs(leftMs - rightMs) >= 1000) change = leftMs > rightMs ? 'Faster in selected run' : 'Slower in selected run';
        rows.push({ key: jobName + '::' + stepName, jobName: primary?.name || other?.name || jobName, stepName: left?.name || right?.name || stepName, leftStatus, rightStatus, leftMs, rightMs, change, severity: !left || !right || leftStatus !== rightStatus ? 'changed' : change !== 'Unchanged' ? 'timing' : 'same' });
      }
    }
    return rows;
  }, [compareEnabled, comparisonRun, jobs, compareDetails.jobs]);
  const compareSummary = useMemo(() => ({
    changed: compareSteps.filter((row) => row.change === 'Outcome changed').length,
    added: compareSteps.filter((row) => row.change === 'Added in selected run').length,
    missing: compareSteps.filter((row) => row.change === 'Missing in selected run').length,
    faster: compareSteps.filter((row) => row.change === 'Faster in selected run').length,
    slower: compareSteps.filter((row) => row.change === 'Slower in selected run').length,
  }), [compareSteps]);

  async function loadRuns() {
    setLoadingRuns(true);
    setError('');
    try {
      const response = await fetch(`${API}/repos/${OWNER_REPO}/actions/runs?per_page=50`, {
        headers: { Accept: 'application/vnd.github+json' },
      });
      if (!response.ok) throw new Error(response.status === 403 ? 'GitHub API rate limit reached. Wait a moment and retry.' : `GitHub returned HTTP ${response.status}.`);
      const payload = await response.json();
      const items = Array.isArray(payload.workflow_runs) ? payload.workflow_runs : [];
      setRuns(items);
      setLastUpdated(new Date().toISOString());
      setSelectedId((current) => { const next = items.some((run) => String(run.id) === current) ? current : (items[0] ? String(items[0].id) : ''); const match = items.find((run) => String(run.id) === next); setSelectedAttempt(match?.run_attempt || 1); return next; });
      if (!items.length) setError('No public workflow runs were returned for this repository.');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load workflow runs.');
    } finally {
      setLoadingRuns(false);
    }
  }

  useEffect(() => { loadRuns(); }, []);

  useEffect(() => {
    if (!selectedRun) { setJobs([]); setArtifacts([]); return undefined; }
    let active = true;
    setLoadingDetails(true);
    setDetailsError('');
    setJobs([]);
    setArtifacts([]);
    setSelectedStepKey('');
    const headers = { Accept: 'application/vnd.github+json' };
    Promise.all([
      fetch(`${API}/repos/${OWNER_REPO}/actions/runs/${selectedRun.id}/attempts/${selectedAttempt}/jobs?per_page=100`, { headers }),
      fetch(`${API}/repos/${OWNER_REPO}/actions/runs/${selectedRun.id}/artifacts?per_page=100`, { headers }),
    ]).then(async ([jobsResponse, artifactsResponse]) => {
      if (!jobsResponse.ok) throw new Error(`Could not load jobs (HTTP ${jobsResponse.status}).`);
      const jobsPayload = await jobsResponse.json();
      let artifactItems = [];
      if (artifactsResponse.ok) {
        const artifactPayload = await artifactsResponse.json();
        artifactItems = Array.isArray(artifactPayload.artifacts) ? artifactPayload.artifacts : [];
      }
      if (!active) return;
      setJobs(Array.isArray(jobsPayload.jobs) ? jobsPayload.jobs : []);
      setArtifacts(artifactItems);
    }).catch((caught) => {
      if (active) setDetailsError(caught instanceof Error ? caught.message : 'Unable to load run details.');
    }).finally(() => { if (active) setLoadingDetails(false); });
    return () => { active = false; };
  }, [selectedId, selectedAttempt]);

  useEffect(() => {
    if (!runs.length) return;
    setCompareId((current) => {
      if (current && current !== selectedId && runs.some((run) => String(run.id) === current)) return current;
      const alternative = runs.find((run) => String(run.id) !== selectedId);
      return alternative ? String(alternative.id) : '';
    });
  }, [runs, selectedId]);

  useEffect(() => {
    if (comparisonRun) setCompareAttempt(comparisonRun.run_attempt || 1);
  }, [comparisonRun?.id]);

  useEffect(() => {
    if (!compareEnabled || !comparisonRun) { setCompareDetails({ jobs: [], artifacts: [], loading: false, error: '' }); return undefined; }
    if (String(comparisonRun.id) === String(selectedRun?.id) && compareAttempt === selectedAttempt) {
      setCompareDetails({ jobs: [], artifacts: [], loading: false, error: 'Choose a different run or attempt for a meaningful comparison.' });
      return undefined;
    }
    let active = true;
    setCompareDetails((current) => ({ ...current, loading: true, error: '' }));
    const jobsUrl = API + '/repos/' + OWNER_REPO + '/actions/runs/' + comparisonRun.id + '/attempts/' + compareAttempt + '/jobs?per_page=100';
    const artifactsUrl = API + '/repos/' + OWNER_REPO + '/actions/runs/' + comparisonRun.id + '/artifacts?per_page=100';
    Promise.all([
      fetch(jobsUrl, { headers: { Accept: 'application/vnd.github+json' } }),
      fetch(artifactsUrl, { headers: { Accept: 'application/vnd.github+json' } }),
    ]).then(async ([jobResponse, artifactResponse]) => {
      if (!jobResponse.ok) throw new Error('Could not load comparison jobs (HTTP ' + jobResponse.status + ').');
      const jobPayload = await jobResponse.json();
      let artifactItems = [];
      if (artifactResponse.ok) {
        const artifactPayload = await artifactResponse.json();
        artifactItems = Array.isArray(artifactPayload.artifacts) ? artifactPayload.artifacts : [];
      }
      if (active) setCompareDetails({ jobs: Array.isArray(jobPayload.jobs) ? jobPayload.jobs : [], artifacts: artifactItems, loading: false, error: '' });
    }).catch((caught) => {
      if (active) setCompareDetails({ jobs: [], artifacts: [], loading: false, error: caught instanceof Error ? caught.message : 'Unable to load comparison run.' });
    });
    return () => { active = false; };
  }, [compareEnabled, compareId, compareAttempt, selectedId, selectedAttempt]);

  useEffect(() => {
    if (tab !== 'logs' || !selectedStep?.jobId) return undefined;
    let active = true;
    setLogsLoading(true); setLogsError(''); setJobLogs([]);
    fetch(`${API}/repos/${OWNER_REPO}/actions/jobs/${selectedStep.jobId}/logs`, { headers: { Accept: 'application/vnd.github+json' } })
      .then(async (response) => {
        if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? 'GitHub did not allow this browser to download the log bundle. Open the job in GitHub to inspect its logs.' : `Could not download job logs (HTTP ${response.status}).`);
        return readZipEntries(await response.arrayBuffer());
      })
      .then((entries) => { if (active) setJobLogs(entries); })
      .catch((caught) => { if (active) setLogsError(caught instanceof Error ? caught.message : 'Unable to read job logs.'); })
      .finally(() => { if (active) setLogsLoading(false); });
    return () => { active = false; };
  }, [tab, selectedStep?.jobId]);

  async function inspectArtifact(artifact) {
    if (artifactContents[artifact.id] || artifactLoading === String(artifact.id)) return;
    setArtifactLoading(String(artifact.id));
    setArtifactErrors((current) => ({ ...current, [artifact.id]: '' }));
    try {
      const response = await fetch(`${API}/repos/${OWNER_REPO}/actions/artifacts/${artifact.id}/zip`, { headers: { Accept: 'application/vnd.github+json' } });
      if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? 'GitHub did not allow browser access to this artifact. Open the run in GitHub to download it.' : `Artifact download failed (HTTP ${response.status}).`);
      const entries = await readZipEntries(await response.arrayBuffer());
      setArtifactContents((current) => ({ ...current, [artifact.id]: entries.map(({ name, text, bytes }) => ({ name, text, size: bytes.byteLength, json: /\\.json$/i.test(name) ? (() => { try { return JSON.parse(text); } catch { return null; } })() : null })) }));
    } catch (caught) { setArtifactErrors((current) => ({ ...current, [artifact.id]: caught instanceof Error ? caught.message : 'Unable to inspect artifact.' })); }
    finally { setArtifactLoading(''); }
  }
  useEffect(() => {
    if (!selectedStepKey && allSteps[0]) setSelectedStepKey(allSteps[0].key);
  }, [allSteps, selectedStepKey]);

  function downloadManifest() {
    if (!selectedRun) return;
    const manifest = {
      schema: 'pathfinder.github-actions-run-manifest/v1',
      generated_at: new Date().toISOString(),
      source: { provider: 'GitHub Actions public REST API', repository: OWNER_REPO, run_url: selectedRun.html_url },
      run: { id: selectedRun.id, run_number: selectedRun.run_number, workflow: selectedRun.name, title: selectedRun.display_title, status: selectedRun.status, conclusion: selectedRun.conclusion, event: selectedRun.event, branch: selectedRun.head_branch, commit: selectedRun.head_sha, attempt_selected: selectedAttempt, attempt_latest: selectedRun.run_attempt, created_at: selectedRun.created_at, started_at: selectedRun.run_started_at, updated_at: selectedRun.updated_at },
      jobs: jobs.map((job) => ({ id: job.id, name: job.name, status: job.status, conclusion: job.conclusion, started_at: job.started_at, completed_at: job.completed_at, html_url: job.html_url, steps: (job.steps || []).map((step) => ({ number: step.number, name: step.name, status: step.status, conclusion: step.conclusion, started_at: step.started_at, completed_at: step.completed_at })) })),
      artifacts: artifacts.map((artifact) => ({ id: artifact.id, name: artifact.name, size_in_bytes: artifact.size_in_bytes, expired: artifact.expired, created_at: artifact.created_at, expires_at: artifact.expires_at, archive_download_url: artifact.archive_download_url })),
      evidence_boundary: 'Manifest contains GitHub-reported run metadata only. It is not a compliance verdict and does not prove ADR satisfaction. Artifact contents are represented only when inspected separately.'
    };
    const blob = new Blob([JSON.stringify(manifest, null, 2)], { type: 'application/json' });
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl; link.download = `pathfinder-run-${selectedRun.id}-attempt-${selectedAttempt}-manifest.json`;
    document.body.appendChild(link); link.click(); link.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  }

  const runUrl = selectedRun?.html_url || `https://github.com/${OWNER_REPO}/actions`;
  const stepOutput = selectedStep ? {
    step: { name: selectedStep.name, number: selectedStep.number, status: selectedStep.status, conclusion: selectedStep.conclusion, started_at: selectedStep.started_at, completed_at: selectedStep.completed_at, duration: duration(selectedStep.started_at, selectedStep.completed_at) },
    job: { id: selectedStep.jobId, name: selectedStep.jobName, conclusion: selectedStep.jobConclusion },
    run: { id: selectedRun?.id, attempt: selectedAttempt, latest_attempt: selectedRun?.run_attempt, revision: selectedRun?.head_sha, branch: selectedRun?.head_branch, event: selectedRun?.event },
    note: 'GitHub Actions exposes step status and timing here. Structured stdout/stderr and generated JSON payloads are not included in the step API response; open the job logs or download a run artifact for those contents.',
  } : null;

  return <div className="run-explorer">
    <section className="run-explorer__hero">
      <div className="run-explorer__hero-copy">
        <div className="run-explorer__eyebrow"><span /> PATHFINDER / EXECUTION TRACE</div>
        <h1>Run Explorer<span>.</span></h1>
        <p>Select a real GitHub Actions run, follow its jobs and steps, and inspect the execution metadata and artifacts behind the result.</p>
        <div className="run-explorer__hero-meta"><span><GitBranch size={14} /> {OWNER_REPO}</span><span><Activity size={14} /> Live public Actions metadata</span></div>
      </div>
      <div className="run-explorer__hero-mark" aria-hidden="true"><div className="run-explorer__mark-ring run-explorer__mark-ring--outer" /><div className="run-explorer__mark-ring run-explorer__mark-ring--inner" /><Workflow size={40} /></div>
    </section>

    <section className="run-explorer__selector" aria-label="Select workflow run">
      <div className="run-explorer__selector-head"><div><span className="run-explorer__kicker">RUN HISTORY</span><h2>Choose an execution</h2></div><button className="run-icon-button" onClick={loadRuns} disabled={loadingRuns} aria-label="Refresh run history"><RefreshCw size={15} className={loadingRuns ? 'run-spin' : ''} /></button></div>
      <label className="run-search"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter by workflow, branch, commit, or run ID" aria-label="Filter workflow runs" /><span>{filteredRuns.length} runs</span></label>
      <div className="run-select-wrap"><Workflow size={17} /><select value={selectedId} onChange={(event) => { const next = event.target.value; setSelectedId(next); setSelectedAttempt(runs.find((run) => String(run.id) === next)?.run_attempt || 1); }} disabled={loadingRuns || !filteredRuns.length} aria-label="Selected workflow run">
        {filteredRuns.length ? filteredRuns.map((run) => <option key={run.id} value={run.id}>#{run.run_number} · {run.name} · {run.display_title || run.head_branch} · {run.conclusion || run.status}</option>) : <option value="">{loadingRuns ? 'Loading runs…' : 'No matching runs'}</option>}
      </select><ChevronDown size={16} /></div>
      {error && <div className="run-inline-alert"><AlertCircle size={16} /><span>{error}</span><a href={`https://github.com/${OWNER_REPO}/actions`} target="_blank" rel="noreferrer">Open Actions <ExternalLink size={13} /></a></div>}
      <div className="run-explorer__selector-foot"><span>{loadingRuns ? 'Refreshing run index…' : `Updated ${lastUpdated ? prettyDate(lastUpdated) : '—'}`}</span><a href={`https://github.com/${OWNER_REPO}/actions`} target="_blank" rel="noreferrer">All workflow runs <ArrowUpRight size={13} /></a></div>
    </section>

    {selectedRun && <>
      <section className="run-summary">
        <div className="run-summary__title"><div><span className="run-explorer__kicker">SELECTED RUN · #{selectedRun.run_number}</span><h2>{selectedRun.display_title || selectedRun.name}</h2><p>{selectedRun.name} · selected attempt {selectedAttempt} of {selectedRun.run_attempt || 1}</p></div><div className="run-summary__controls"><Status value={selectedRun.conclusion || selectedRun.status} /><button className="run-manifest-button" onClick={downloadManifest} disabled={loadingDetails || !jobs.length}><ArrowDownToLine size={15} /> Export run manifest</button></div></div>
        <div className="run-summary__grid">
          <div><span>TRIGGER</span><strong>{selectedRun.event || '—'}</strong></div>
          <div><span>BRANCH</span><strong>{selectedRun.head_branch || '—'}</strong></div>
          <div><span>REVISION</span><strong className="run-mono">{(selectedRun.head_sha || '').slice(0, 12) || '—'}</strong></div>
          <div><span>DURATION</span><strong>{duration(selectedRun.run_started_at || selectedRun.created_at, selectedRun.updated_at)}</strong></div>
        </div>
        <div className="run-summary__bottom"><span><Clock3 size={14} /> Started {prettyDate(selectedRun.run_started_at || selectedRun.created_at)}</span><div className="run-summary__links"><label className="run-attempt-picker">Attempt <select aria-label="Workflow run attempt" value={selectedAttempt} onChange={(event) => setSelectedAttempt(Number(event.target.value))}>{Array.from({ length: Math.max(1, selectedRun.run_attempt || 1) }, (_, index) => index + 1).map((attempt) => <option key={attempt} value={attempt}>#{attempt}{attempt === (selectedRun.run_attempt || 1) ? ' · latest' : ''}</option>)}</select></label><a href={runUrl} target="_blank" rel="noreferrer">Open run in GitHub <ArrowUpRight size={14} /></a></div></div>
      </section>

      <section className="run-comparison" aria-labelledby="run-comparison-title">
        <div className="run-comparison__heading"><div><span className="run-explorer__kicker">REGRESSION WORKSPACE</span><h2 id="run-comparison-title">Compare executions</h2><p>Compare actual GitHub-reported step outcomes, timings, revisions, and artifact inventories across runs or rerun attempts.</p></div><label className="run-compare-toggle"><input type="checkbox" checked={compareEnabled} onChange={(event) => setCompareEnabled(event.target.checked)} /> Enable comparison</label></div>
        {compareEnabled && <>
          <div className="run-comparison__selectors">
            <div><span>BASELINE · SELECTED RUN</span><strong>#{selectedRun.run_number} · attempt {selectedAttempt}</strong><small>{selectedRun.head_sha?.slice(0, 12)} · {selectedRun.conclusion || selectedRun.status}</small></div>
            <div><span>COMPARE AGAINST</span><select aria-label="Run to compare against" value={compareId} onChange={(event) => { setCompareId(event.target.value); setCompareAttempt(runs.find((run) => String(run.id) === event.target.value)?.run_attempt || 1); }}><option value="">Choose another run…</option>{runs.filter((run) => String(run.id) !== selectedId).map((run) => <option key={run.id} value={run.id}>#{run.run_number} · {run.name} · {run.display_title || run.head_branch}</option>)}</select>{comparisonRun && <small>{comparisonRun.head_sha?.slice(0, 12)} · {comparisonRun.conclusion || comparisonRun.status}</small>}</div>
            {comparisonRun && <label className="run-attempt-picker">Other attempt <select value={compareAttempt} onChange={(event) => setCompareAttempt(Number(event.target.value))}>{Array.from({ length: Math.max(1, comparisonRun.run_attempt || 1) }, (_, index) => index + 1).map((attempt) => <option key={attempt} value={attempt}>#{attempt}{attempt === (comparisonRun.run_attempt || 1) ? ' · latest' : ''}</option>)}</select></label>}
          </div>
          {compareDetails.error && <div className="run-inline-alert"><AlertCircle size={15} /><span>{compareDetails.error}</span></div>}
          {compareDetails.loading && <div className="run-loading run-loading--compact"><LoaderCircle size={16} className="run-spin" /> Loading comparison execution…</div>}
          {!compareDetails.loading && !compareDetails.error && comparisonRun && <div className="run-comparison__body">
            <div className="run-comparison__metrics"><div><span>Outcome changes</span><strong>{compareSummary.changed}</strong></div><div><span>Steps added</span><strong>{compareSummary.added}</strong></div><div><span>Steps missing</span><strong>{compareSummary.missing}</strong></div><div><span>Faster / slower</span><strong>{compareSummary.faster} / {compareSummary.slower}</strong></div></div>
            <div className="run-comparison__revision"><div><span>Selected revision</span><code>{selectedRun.head_sha || 'Unavailable'}</code></div><GitBranch size={16} /><div><span>Comparison revision</span><code>{comparisonRun.head_sha || 'Unavailable'}</code></div></div>
            <div className="run-comparison__table-wrap"><table className="run-comparison__table"><thead><tr><th>Job / step</th><th>Selected</th><th>Compared</th><th>Selected duration</th><th>Compared duration</th><th>Difference</th></tr></thead><tbody>{compareSteps.map((row) => <tr key={row.key} className={row.severity === 'changed' ? 'is-changed' : ''}><td><strong>{row.stepName}</strong><small>{row.jobName}</small></td><td><Status value={row.leftStatus === 'missing' ? 'unknown' : row.leftStatus} /></td><td><Status value={row.rightStatus === 'missing' ? 'unknown' : row.rightStatus} /></td><td>{row.leftMs === null ? '—' : Math.round(row.leftMs / 1000) + 's'}</td><td>{row.rightMs === null ? '—' : Math.round(row.rightMs / 1000) + 's'}</td><td><span className={'run-change run-change--' + row.severity}>{row.change}</span></td></tr>)}</tbody></table></div>
            <div className="run-comparison__artifacts"><div><span className="run-explorer__kicker">OUTPUT INVENTORY</span><strong>Artifact changes</strong><p>Artifacts are compared by name and size. Inspect matching bundles from each run’s Artifacts tab to compare individual JSON/file contents.</p></div><div className="run-artifact-diff-list">{Array.from(new Set([...artifacts.map((x) => x.name), ...compareDetails.artifacts.map((x) => x.name)])).map((name) => { const left = artifacts.find((x) => x.name === name); const right = compareDetails.artifacts.find((x) => x.name === name); const change = !left ? 'Only comparison run' : !right ? 'Only selected run' : left.size_in_bytes === right.size_in_bytes ? 'Same size' : (left.size_in_bytes > right.size_in_bytes ? 'Selected run larger' : 'Comparison run larger'); return <div key={name}><strong>{name}</strong><small>Selected: {left ? Math.ceil(left.size_in_bytes / 1024) + ' KB' : '—'} · Compared: {right ? Math.ceil(right.size_in_bytes / 1024) + ' KB' : '—'}</small><span>{change}</span></div>; })}</div></div>
          </div>}
        </>}
      </section>

      <section className="run-signal-graph" aria-label="Execution signal flow">
        <div className="run-signal-graph__heading"><div><span className="run-explorer__kicker">SIGNAL FLOW</span><h2>Run → jobs → artifacts</h2></div><span>{jobs.length} jobs · {allSteps.length} steps · {artifacts.length} artifacts</span></div>
        <div className="run-graph-track">
          <div className="run-graph-node run-graph-node--source"><span className="run-graph-node__type">SOURCE RUN</span><strong>#{selectedRun.run_number}</strong><small>{selectedRun.name}</small><Status value={selectedRun.conclusion || selectedRun.status} /></div>
          <div className="run-graph-connector" aria-hidden="true"><span /></div>
          {jobs.map((job) => <React.Fragment key={job.id}><button className={`run-graph-node run-graph-node--job ${job.conclusion === 'failure' ? 'is-failed' : ''}`} onClick={() => { const first = allSteps.find((step) => step.jobId === job.id); if (first) { setSelectedStepKey(first.key); setTab('summary'); } }}><span className="run-graph-node__type">JOB · {job.id}</span><strong>{job.name}</strong><small>{(job.steps || []).length} steps · {duration(job.started_at, job.completed_at)}</small><Status value={job.conclusion || job.status} /></button><div className="run-graph-connector" aria-hidden="true"><span /></div></React.Fragment>)}
          <div className="run-graph-node run-graph-node--artifact"><span className="run-graph-node__type">OUTPUTS</span><strong>{artifacts.length} artifacts</strong><small>{artifacts.length ? 'Inspectable run bundles' : 'No artifacts reported'}</small><button onClick={() => setTab('artifacts')}>Inspect outputs <ArrowUpRight size={13} /></button></div>
        </div>
        <p className="run-signal-graph__note">Connectors show the execution hierarchy reported by GitHub, not a dependency graph between jobs. Selecting a job focuses its first reported step.</p>
      </section>
      <div className="run-explorer__section-heading"><div><span className="run-explorer__kicker">EXECUTION GRAPH</span><h2>Jobs & steps</h2></div><p>Select any step to inspect its status, timing, parent job, and available run outputs.</p></div>
      {detailsError && <div className="run-inline-alert"><AlertCircle size={16} /><span>{detailsError}</span><a href={runUrl} target="_blank" rel="noreferrer">View run <ExternalLink size={13} /></a></div>}
      {loadingDetails ? <div className="run-loading"><LoaderCircle size={19} className="run-spin" /> Loading jobs, steps, and artifacts…</div> : <div className="run-workspace">
        <section className="run-step-panel" aria-label="Workflow steps">
          <div className="run-step-panel__top"><div><span className="run-explorer__kicker">TRACE</span><strong>{jobs.length} jobs · {allSteps.length} steps</strong></div><span className="run-step-count">{completedSteps}/{allSteps.length} complete</span></div>
          {jobs.length ? jobs.map((job, jobIndex) => <div className="run-job" key={job.id}>
            <div className="run-job__heading"><span className="run-job__index">{String(jobIndex + 1).padStart(2, '0')}</span><div><strong>{job.name}</strong><small>{job.steps?.length || 0} steps · {duration(job.started_at, job.completed_at)}</small></div><Status value={job.conclusion || job.status} /></div>
            <div className="run-job__steps">{(job.steps || []).map((step, index) => {
              const key = `${job.id}:${step.number ?? index}`;
              const active = key === (selectedStep?.key || selectedStepKey);
              return <button type="button" className={`run-step ${active ? 'is-selected' : ''}`} key={key} onClick={() => { setSelectedStepKey(key); setTab('summary'); }}>
                <span className={`run-step__dot run-step__dot--${toneFor(step.conclusion || step.status)}`} />
                <span className="run-step__copy"><strong>{titleForStep(step)}</strong><small>{duration(step.started_at, step.completed_at)}{step.number ? ` · step ${step.number}` : ''}</small></span>
                <Status value={step.conclusion || step.status} />
              </button>;
            })}</div>
          </div>) : <div className="run-empty"><CircleDashed size={24} /><strong>No step data available</strong><span>Open the run in GitHub to inspect its execution.</span></div>}
          {failedSteps > 0 && <div className="run-failure-note"><AlertCircle size={15} /> {failedSteps} step{failedSteps === 1 ? '' : 's'} failed. Select a failed step to inspect its metadata and open the job logs.</div>}
        </section>

        <section className="run-inspector" aria-label="Selected step details">
          {selectedStep ? <>
            <div className="run-inspector__head"><div><span className="run-explorer__kicker">STEP INSPECTOR</span><h3>{titleForStep(selectedStep)}</h3><p>{selectedStep.jobName}</p></div><Status value={selectedStep.conclusion || selectedStep.status} /></div>
            <div className="run-inspector__tabs" role="tablist" aria-label="Step detail tabs">{[['summary','Summary'],['inputs','Inputs'],['outputs','Outputs'],['logs','Logs'],['evidence','Evidence'],['artifacts','Artifacts']].map(([key,label]) => <button key={key} role="tab" aria-selected={tab === key} className={tab === key ? 'is-active' : ''} onClick={() => setTab(key)}>{label}</button>)}</div>
            {tab === 'summary' && <div className="run-inspector__body">
              <div className="run-inspector__state"><span className={`run-step__dot run-step__dot--${toneFor(selectedStep.conclusion || selectedStep.status)}`} /><div><strong>{STATES[selectedStep.conclusion || selectedStep.status]?.label || selectedStep.status || 'Unknown'}</strong><span>Actual GitHub Actions step metadata</span></div></div>
              <dl className="run-detail-list"><div><dt>Step started</dt><dd>{prettyDate(selectedStep.started_at)}</dd></div><div><dt>Step completed</dt><dd>{prettyDate(selectedStep.completed_at)}</dd></div><div><dt>Duration</dt><dd>{duration(selectedStep.started_at, selectedStep.completed_at)}</dd></div><div><dt>Step number</dt><dd>{selectedStep.number ?? '—'}</dd></div><div><dt>Job ID</dt><dd className="run-mono">{selectedStep.jobId}</dd></div><div><dt>Conclusion</dt><dd>{selectedStep.conclusion || 'Not final'}</dd></div></dl>
              <div className="run-inspector__actions"><a href={selectedStep.jobUrl || runUrl} target="_blank" rel="noreferrer"><FileText size={15} /> Open job details <ArrowUpRight size={13} /></a><a href={runUrl} target="_blank" rel="noreferrer"><ExternalLink size={15} /> Run overview</a></div>
            </div>}
            {tab === 'inputs' && <div className="run-inspector__body"><div className="run-data-callout"><FileJson2 size={17} /><div><strong>Step inputs</strong><p>GitHub’s public job-step API does not expose action input values or shell environment variables. This panel shows only metadata actually returned for this step; it will not infer inputs from a workflow name or log text.</p></div></div><pre className="run-json"><code>{safeJson({ available: false, reason: 'The public GitHub Actions step API does not provide resolved inputs or environment values.', step: { name: selectedStep.name, number: selectedStep.number, job: selectedStep.jobName, job_id: selectedStep.jobId }, source: selectedStep.jobUrl })}</code></pre></div>}
            {tab === 'evidence' && <div className="run-inspector__body"><div className="run-data-callout"><ShieldAlert size={17} /><div><strong>Execution provenance</strong><p>These fields identify the selected GitHub execution. They establish what GitHub reports about the run, not whether an architectural decision is satisfied.</p></div></div><dl className="run-detail-list"><div><dt>Repository</dt><dd>{OWNER_REPO}</dd></div><div><dt>Workflow</dt><dd>{selectedRun.name}</dd></div><div><dt>Run ID</dt><dd className="run-mono">{selectedRun.id}</dd></div><div><dt>Selected attempt</dt><dd>{selectedAttempt}{selectedAttempt === (selectedRun.run_attempt || 1) ? ' · latest' : ''}</dd></div><div><dt>Latest attempt</dt><dd>{selectedRun.run_attempt || 1}</dd></div><div><dt>Commit SHA</dt><dd className="run-mono">{selectedRun.head_sha}</dd></div><div><dt>Branch</dt><dd>{selectedRun.head_branch || '—'}</dd></div><div><dt>Trigger</dt><dd>{selectedRun.event || '—'}</dd></div><div><dt>Step job ID</dt><dd className="run-mono">{selectedStep.jobId}</dd></div><div><dt>Step name</dt><dd>{selectedStep.name}</dd></div><div><dt>Step result</dt><dd>{selectedStep.conclusion || selectedStep.status || 'Unknown'}</dd></div></dl><div className="run-inspector__actions"><a href={selectedRun.html_url} target="_blank" rel="noreferrer"><ExternalLink size={15} /> Source run</a><a href={`https://github.com/${OWNER_REPO}/commit/${selectedRun.head_sha}`} target="_blank" rel="noreferrer"><GitBranch size={15} /> Source commit</a></div></div>}
            {tab === 'outputs' && <div className="run-inspector__body"><div className="run-data-callout"><FileJson2 size={17} /><div><strong>Structured step outputs</strong><p>GitHub does not return arbitrary step output values through the public job API. Inspect the artifacts below for JSON or other output files uploaded by the workflow.</p></div></div><pre className="run-json"><code>{safeJson(stepOutput)}</code></pre><button className="run-copy-hint" onClick={() => navigator.clipboard?.writeText(safeJson(stepOutput))}>Copy step metadata</button><p className="run-muted-note">No output payload is claimed unless it is present in a real artifact or log.</p></div>}
            {tab === 'artifacts' && <div className="run-inspector__body"><div className="run-artifact-intro"><strong>{artifacts.length} artifacts attached to this run</strong><span>Artifacts are run-level bundles; GitHub does not identify an artifact as belonging to a single step unless the workflow names or manifests it.</span></div>{artifacts.length ? artifacts.map((artifact) => <div className="run-artifact" key={artifact.id}><FileJson2 size={18} /><div><strong>{artifact.name}</strong><span>{Math.max(1, Math.round((artifact.size_in_bytes || 0) / 1024))} KB · expires {prettyDate(artifact.expires_at)}</span></div><a href={runUrl} target="_blank" rel="noreferrer" aria-label={`Open artifact ${artifact.name} in GitHub`}><ArrowDownToLine size={15} /></a></div>) : <div className="run-empty run-empty--compact"><FileJson2 size={21} /><strong>No artifacts reported</strong><span>This run may not upload output bundles.</span></div>}<a className="run-primary-link" href={runUrl} target="_blank" rel="noreferrer">Open run artifacts in GitHub <ArrowUpRight size={14} /></a></div>}
            {tab === 'logs' && <div className="run-inspector__body"><div className="run-data-callout"><FileText size={17} /><div><strong>Actual job log files</strong><p>Loaded from the GitHub Actions job log archive when the browser and GitHub permit it. Log contents are raw observations, not compliance verdicts.</p></div></div>{logsLoading && <div className="run-loading run-loading--compact"><LoaderCircle size={16} className="run-spin" /> Downloading and reading job logs…</div>}{logsError && <div className="run-inline-alert"><AlertCircle size={15} /><span>{logsError}</span><a href={selectedStep.jobUrl || runUrl} target="_blank" rel="noreferrer">Open in GitHub <ExternalLink size={13} /></a></div>}{!logsLoading && !logsError && jobLogs.length > 0 && <div className="run-log-files">{jobLogs.map((entry) => <details className="run-log-file" key={entry.name}><summary><FileText size={14} />{entry.name}<span>{entry.text.split(String.fromCharCode(10)).length} lines</span></summary><pre><code>{entry.text || '(no output)'}</code></pre></details>)}</div>}{!logsLoading && !logsError && !visibleStepLogs.length && <div className="run-empty run-empty--compact"><FileText size={21} /><strong>No log entries returned</strong><span>GitHub may not retain logs for this run.</span></div>}{!logsLoading && !logsError && visibleStepLogs.length > 0 && <>{!matchingStepLogs.length && <p className="run-muted-note">GitHub’s archive did not clearly map files to this step; showing the full log set for its parent job.</p>}<div className="run-log-files">{visibleStepLogs.map((entry) => <details className="run-log-file" key={entry.name} open={matchingStepLogs.length === 1}><summary><FileText size={14} />{entry.name}<span>{entry.text.split(String.fromCharCode(10)).length} lines</span></summary><pre><code>{entry.text}</code></pre></details>)}</div></>}<a className="run-log-link" href={selectedStep.jobUrl || runUrl} target="_blank" rel="noreferrer"><FileText size={17} /><span><strong>Open {selectedStep.jobName} in GitHub</strong><small>Fallback if log download is unavailable.</small></span><ArrowUpRight size={15} /></a></div>}
            {tab === 'artifacts' && <div className="run-inspector__body"><div className="run-artifact-intro"><strong>{artifacts.length} artifacts attached to this run</strong><span>Artifacts belong to the run unless their own manifest identifies a step or source. Open an artifact to inspect real files and parse valid JSON files.</span></div>{artifacts.length ? artifacts.map((artifact) => <div className="run-artifact-wrap" key={artifact.id}><div className="run-artifact"><FileJson2 size={18} /><div><strong>{artifact.name}</strong><span>{Math.max(1, Math.round((artifact.size_in_bytes || 0) / 1024))} KB · expires {prettyDate(artifact.expires_at)}</span><small>Artifact ID {artifact.id} · {artifact.expired ? 'expired' : 'available according to GitHub'}</small></div><button className="run-artifact-inspect" onClick={() => inspectArtifact(artifact)} disabled={artifact.expired || artifactLoading === String(artifact.id)}>{artifactLoading === String(artifact.id) ? <LoaderCircle size={15} className="run-spin" /> : <Search size={15} />}{artifactContents[artifact.id] ? 'Loaded' : 'Inspect files'}</button></div>{artifactErrors[artifact.id] && <div className="run-inline-alert"><AlertCircle size={14} /><span>{artifactErrors[artifact.id]}</span></div>}{artifactContents[artifact.id]?.map((file) => <details className="run-log-file" key={file.name}><summary><FileText size={14} />{file.name}<span>{Math.max(1, Math.round(file.size / 1024))} KB</span></summary>{file.json !== null ? <pre className="run-json"><code>{safeJson(file.json)}</code></pre> : <pre><code>{file.text.slice(0, 300000) || '(empty file)'}</code></pre>}</details>)}</div>) : <div className="run-empty run-empty--compact"><FileJson2 size={21} /><strong>No artifacts reported</strong><span>This run may not upload output bundles.</span></div>}<a className="run-primary-link" href={runUrl} target="_blank" rel="noreferrer">Open run artifacts in GitHub <ArrowUpRight size={14} /></a></div>}
          </> : <div className="run-empty"><CircleDashed size={24} /><strong>Select a workflow step</strong><span>Its execution details will appear here.</span></div>}
        </section>
      </div>}
      <section className="run-explorer__footnote"><ShieldAlert size={16} /><p><strong>Evidence boundary.</strong> This page reads live public GitHub Actions metadata. Step status and timing are authoritative for execution state, but they are not proof of ADR compliance. Artifact contents are not fabricated or inferred; where detailed payloads are not available through the public API, the UI links to the source run.</p></section>
    </>}
  </div>;
}
