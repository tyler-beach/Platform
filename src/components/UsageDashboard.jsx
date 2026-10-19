import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Activity, AlertCircle, CheckCircle2, CircleHelp, Clock3, RefreshCw, ShieldAlert, XCircle } from 'lucide-react';
import { AGGREGATE_STATUS_KEYS, OUTCOME_KEYS, STAGE_KEYS, aggregateStageMetrics, ratio, usageSnapshotURL, validateUsageSnapshot } from '../usage-dashboard-data.js';

const OWNER_REPO = document.querySelector('meta[name="adr-repository"]')?.content || 'tyler-beach/Platform';
const SNAPSHOT_URL = usageSnapshotURL(import.meta.env.BASE_URL || '/');
const WORKFLOW_URL = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(OWNER_REPO) ? `https://github.com/${OWNER_REPO}/actions/workflows/pathfinder-issue-analyze.yml` : 'https://github.com/tyler-beach/Platform/actions/workflows/pathfinder-issue-analyze.yml';
const REFRESH_MS = 5 * 60 * 1000;
const OUTCOME_LABELS = {
  supported_deviation: 'Supported deviation',
  no_deviation_found: 'Aligned finding (no deviation found)',
  inconclusive: 'Inconclusive',
  not_applicable: 'Not applicable',
};
const STATUS_LABELS = {
  all_aligned: 'All aligned',
  deviations_found: 'Deviations found',
  mixed: 'Partial alignment / mixed',
  insufficient_coverage: 'Insufficient evidence',
  not_applicable_only: 'No in-scope requirements',
  other: 'Other or legacy status',
};
const STAGE_LABELS = {
  catalog_load: 'Catalog load', evaluation: 'Requirement evaluation', intake: 'Issue intake', ledger: 'Ledger record',
  other: 'Other bounded stage', package_build: 'Package build', publication: 'Comment publication', report_write: 'Report write', summary: 'Summary',
};
const prettyDate = (value) => new Date(value).toLocaleString();

function Metric({ label, value, detail, icon: Icon }) {
  return <article className="usage-metric"><div><span>{label}</span><Icon size={17} aria-hidden="true" /></div><strong>{value}</strong><small>{detail}</small></article>;
}

export default function UsageDashboard() {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [lastChecked, setLastChecked] = useState('');
  const [telemetryDays, setTelemetryDays] = useState(90);
  const [telemetryStage, setTelemetryStage] = useState('all');
  const activeRequest = useRef(null);
  const outcomeTotal = useMemo(() => snapshot ? OUTCOME_KEYS.reduce((sum, key) => sum + snapshot.totals.outcomes[key], 0) : 0, [snapshot]);
  const alignedShare = snapshot ? ratio(snapshot.totals.aggregate_statuses.all_aligned, snapshot.totals.succeeded) : null;
  const recentDays = useMemo(() => (snapshot?.daily || []).slice(-14), [snapshot]);
  const stageQuery = useMemo(() => snapshot ? aggregateStageMetrics(snapshot.daily, snapshot.generated_at, Math.min(telemetryDays, snapshot.window_days), telemetryStage) : { activeDays: 0, rows: [] }, [snapshot, telemetryDays, telemetryStage]);
  const maxDaily = Math.max(1, ...recentDays.map((day) => day.jobs));
  const isStale = snapshot ? Date.now() - Date.parse(snapshot.generated_at) > 24 * 60 * 60 * 1000 : false;
  const hasNoRecords = snapshot?.records_seen === 0;

  const refresh = useCallback(async ({ quiet = false } = {}) => {
    if (!SNAPSHOT_URL) {
      setError('The dashboard data source is not configured for this repository.');
      setLoading(false);
      return;
    }
    if (!quiet) setRefreshing(true);
    setError('');
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(`${SNAPSHOT_URL}?refresh=${Date.now()}`, { cache: 'no-store', signal: controller.signal, headers: { Accept: 'application/json' } });
      if (response.status === 404) throw new Error('No dashboard snapshot is available yet. Run a Pathfinder analysis to create it.');
      if (!response.ok) throw new Error(`Dashboard data could not be loaded (HTTP ${response.status}).`);
      const parsed = validateUsageSnapshot(await response.json());
      setSnapshot(parsed);
      setLastChecked(new Date().toISOString());
    } catch (caught) {
      setError(caught?.name === 'AbortError' ? 'Dashboard data request timed out. The last loaded snapshot is preserved.' : (caught instanceof Error ? caught.message : 'Dashboard data could not be loaded.'));
    } finally {
      window.clearTimeout(timeout);
      if (activeRequest.current === controller) activeRequest.current = null;
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    refresh();
    const interval = window.setInterval(() => { if (active) refresh({ quiet: true }); }, REFRESH_MS);
    return () => { active = false; window.clearInterval(interval); activeRequest.current?.abort(); };
  }, [refresh]);

  return <div className="usage-page">
    <header className="usage-hero">
      <div><span className="usage-kicker"><Activity size={14} /> PATHFINDER / USAGE</span><h1>Usage &amp; outcomes</h1><p>Aggregate activity recorded by the GitHub Actions Pathfinder PoC. Completed analysis runs refresh this access-controlled Pages snapshot through a site deployment.</p></div>
      <button type="button" className="usage-refresh" onClick={() => refresh()} disabled={refreshing}><RefreshCw size={15} className={refreshing ? 'usage-spin' : ''} />{refreshing ? 'Refreshing' : 'Refresh now'}</button>
    </header>

    <div className={`usage-status ${error ? 'usage-status--warning' : isStale ? 'usage-status--warning' : ''}`} role="status" aria-live="polite">
      {error ? <AlertCircle size={16} /> : hasNoRecords ? <CircleHelp size={16} /> : isStale ? <Clock3 size={16} /> : <CheckCircle2 size={16} />}
      <span>{error || (loading ? 'Loading the latest aggregate…' : hasNoRecords ? 'No aggregate records are published. No alignment or deviation conclusion can be drawn.' : isStale ? 'The latest available snapshot is more than 24 hours old.' : 'Snapshot is current.')}</span>
      {snapshot && <small>Generated {prettyDate(snapshot.generated_at)}{lastChecked ? ` · checked ${prettyDate(lastChecked)}` : ''}</small>}
    </div>

    {!snapshot && !loading ? <section className="usage-empty"><CircleHelp size={22} /><h2>Usage data unavailable</h2><p>{error || 'Run a Pathfinder analysis to create the first aggregate snapshot.'}</p><a href={WORKFLOW_URL} target="_blank" rel="noreferrer">Open Pathfinder workflow</a></section> : null}

    {snapshot && hasNoRecords ? <section className="usage-empty"><CircleHelp size={22} /><h2>No usage data yet</h2><p>This Pages deployment contains no aggregate records. If the site is public or its privacy could not be verified, this empty snapshot is intentional. No alignment or deviation conclusion can be drawn.</p><a href={WORKFLOW_URL} target="_blank" rel="noreferrer">Open Pathfinder workflow</a></section> : null}

    {snapshot && !hasNoRecords && <>
      <section className="usage-metrics" aria-label="Analysis totals">
        <Metric label="Analyses" value={snapshot.totals.jobs.toLocaleString()} detail={`${snapshot.window_days}-day window · ${snapshot.totals.succeeded} completed · ${snapshot.totals.failed} failed`} icon={Activity} />
        <Metric label="All aligned" value={snapshot.totals.aggregate_statuses.all_aligned.toLocaleString()} detail={alignedShare === null ? 'No completed analyses' : `${(alignedShare * 100).toFixed(1)}% of completed analyses`} icon={CheckCircle2} />
        <Metric label="Deviations found" value={snapshot.totals.aggregate_statuses.deviations_found.toLocaleString()} detail="Analyses with supported deviations" icon={ShieldAlert} />
        <Metric label="Partial alignment" value={snapshot.totals.aggregate_statuses.mixed.toLocaleString()} detail="Mixed aligned, deviating, or uncertain results" icon={CircleHelp} />
      </section>

      <section className="usage-panel" aria-labelledby="usage-trend-title">
        <div className="usage-panel__heading"><div><span className="usage-kicker">ACTIVITY</span><h2 id="usage-trend-title">Daily analyses</h2></div><span>{snapshot.daily.length} active days · last {snapshot.window_days} days</span></div>
        {recentDays.length ? <div className="usage-trend" role="img" aria-label={`Daily analyses: ${recentDays.map((day) => `${day.date}: ${day.jobs}`).join(', ')}`}>
          {recentDays.map((day) => <div className="usage-trend__day" key={day.date} title={`${day.date}: ${day.jobs} analyses`}><span>{day.jobs || ''}</span><div><i style={{ height: `${Math.max(day.jobs ? 4 : 0, (day.jobs / maxDaily) * 100)}%` }} /></div><small>{day.date.slice(5)}</small></div>)}
        </div> : <p className="usage-muted">No analyses in this reporting window.</p>}
        <p className="usage-muted">Bars show analysis jobs. They are not findings or a compliance score.</p>
      </section>

      <section className="usage-lower-grid">
        <div className="usage-panel"><div className="usage-panel__heading"><div><span className="usage-kicker">ANALYSIS STATUS</span><h2>Aggregate results</h2></div><span>{snapshot.totals.succeeded} completed</span></div>
          <ul className="usage-outcomes">{AGGREGATE_STATUS_KEYS.map((key) => <li key={key}><span>{STATUS_LABELS[key]}</span><strong>{snapshot.totals.aggregate_statuses[key].toLocaleString()}</strong></li>)}</ul>
          <p className="usage-muted">Status is computed per analyzed package. It is not an organizational compliance score.</p>
        </div>
        <div className="usage-panel"><div className="usage-panel__heading"><div><span className="usage-kicker">OUTCOMES</span><h2>Finding counts</h2></div><span>{outcomeTotal.toLocaleString()} total findings</span></div>
          <ul className="usage-outcomes">{OUTCOME_KEYS.map((key) => <li key={key}><span>{OUTCOME_LABELS[key]}</span><strong>{snapshot.totals.outcomes[key].toLocaleString()}</strong></li>)}</ul>
          <p className="usage-muted">Counts are findings across completed analyses, not unique analyses. “Aligned” means no deviation was found for that requirement. No outcome is proof of organizational compliance.</p>
        </div>
        <div className="usage-panel usage-ai-panel"><div className="usage-panel__heading"><div><span className="usage-kicker">MODEL METERING</span><h2>AI usage &amp; spend</h2></div><XCircle size={17} aria-hidden="true" /></div>
          <strong>Not metered in this PoC</strong><p>The current Pathfinder workflow does not call an AI model. Token usage and model spend are unavailable, not zero. OTel traces do not serve as a billing ledger.</p>
        </div>
      </section>
      <section className="usage-panel usage-telemetry-panel" aria-labelledby="usage-telemetry-title">
        <div className="usage-panel__heading"><div><span className="usage-kicker">OPEN TELEMETRY · WORKFLOW MEASUREMENTS</span><h2 id="usage-telemetry-title">Stage performance and errors</h2></div><span>{stageQuery.activeDays} active days · selected range</span></div>
        <div className="usage-query-controls">
          <label>Time range<select value={Math.min(telemetryDays, snapshot.window_days)} onChange={(event) => setTelemetryDays(Number(event.target.value))}>
            {[7, 30, 90].filter((days) => days <= snapshot.window_days).map((days) => <option key={days} value={days}>{days} days</option>)}
          </select></label>
          <label>Stage<select value={telemetryStage} onChange={(event) => setTelemetryStage(event.target.value)}>
            <option value="all">All stages</option>{STAGE_KEYS.map((stage) => <option key={stage} value={stage}>{STAGE_LABELS[stage]}</option>)}
          </select></label>
        </div>
        {snapshot.operational_telemetry === 'available' && stageQuery.rows.some((metric) => metric.runs > 0) ? <div className="usage-table-wrap"><table className="usage-telemetry-table"><thead><tr><th scope="col">Stage</th><th scope="col">Runs</th><th scope="col">Errors</th><th scope="col">Skipped</th><th scope="col">Mean duration</th><th scope="col">Max duration</th></tr></thead><tbody>
          {stageQuery.rows.map((metric) => {
            const { stage } = metric;
            const meanMs = metric.runs ? metric.duration_total_ns / metric.runs / 1e6 : null;
            const maxMs = metric.duration_max_ns ? metric.duration_max_ns / 1e6 : null;
            return <tr key={stage}><th scope="row">{STAGE_LABELS[stage]}</th><td>{metric.runs.toLocaleString()}</td><td>{metric.errors.toLocaleString()}</td><td>{metric.skipped.toLocaleString()}</td><td>{meanMs === null ? '—' : `${meanMs.toFixed(2)} ms`}</td><td>{maxMs === null ? '—' : `${maxMs.toFixed(2)} ms`}</td></tr>;
          })}
        </tbody></table></div> : <p className="usage-muted">Stage measurements have not been captured for this selected reporting window yet. New analysis runs will populate this table.</p>}
        <p className="usage-muted">Durations are measured by the Go workflow instrumentation. The dashboard stores bounded counts and duration aggregates; it does not expose raw traces, source, issue IDs, or run IDs.</p>
      </section>
      <p className="usage-source-note">Projection diagnostics: {snapshot.records_seen} ledger records read, {snapshot.rejected_records} invalid records excluded. Refreshes every five minutes while this page is open.</p>
    </>}
  </div>;
}
