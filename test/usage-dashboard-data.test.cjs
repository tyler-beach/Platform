const test = require('node:test');
const assert = require('node:assert/strict');

test('accepts a valid bounded dashboard projection and normalizes allowlisted values', async () => {
  const { validateUsageSnapshot, usageSnapshotURL, ratio, STAGE_KEYS } = await import('../src/usage-dashboard-data.js');
  const operational = Object.fromEntries(STAGE_KEYS.map((stage) => [stage, { runs: 0, errors: 0, skipped: 0, duration_total_ns: 0, duration_max_ns: 0 }]));
  operational.evaluation = { runs: 2, errors: 1, skipped: 0, duration_total_ns: 2500000, duration_max_ns: 2000000 };
  const snapshot = validateUsageSnapshot({
    schema_version: 'pathfinder-usage-dashboard-v2',
    generated_at: '2026-10-19T12:00:00Z',
    window_days: 90,
    records_seen: 3,
    rejected_records: 0,
    totals: {
      jobs: 3, succeeded: 2, failed: 1,
      aggregate_statuses: { all_aligned: 1, deviations_found: 0, mixed: 1, insufficient_coverage: 0, not_applicable_only: 0, other: 0 },
      outcomes: { supported_deviation: 1, no_deviation_found: 1, inconclusive: 2, not_applicable: 0 },
      operational_metrics: operational,
    },
    daily: [{ date: '2026-10-19', jobs: 3, succeeded: 2, failed: 1,
      aggregate_statuses: { all_aligned: 1, deviations_found: 0, mixed: 1, insufficient_coverage: 0, not_applicable_only: 0, other: 0 },
      outcomes: { supported_deviation: 1, no_deviation_found: 1, inconclusive: 2, not_applicable: 0 },
      operational_metrics: operational }],
    model_metering: 'not_metered',
    operational_telemetry: 'available',
  });
  assert.equal(snapshot.totals.jobs, 3);
  assert.equal(snapshot.totals.aggregate_statuses.mixed, 1);
  assert.equal(snapshot.totals.outcomes.inconclusive, 2);
  assert.equal(snapshot.daily.length, 1);
  assert.equal(snapshot.totals.operational_metrics.evaluation.duration_total_ns, 2500000);
  assert.equal(usageSnapshotURL('/'), '/data/summary.json');
  assert.equal(usageSnapshotURL('/Platform/'), '/Platform/data/summary.json');
  assert.equal(usageSnapshotURL('https://evil.example/'), null);
  assert.equal(ratio(2, 4), 0.5);
  assert.equal(ratio(0, 0), null);
});

test('rejects invalid counts, unknown outcomes, stale schemas, and unbounded buckets', async () => {
  const { validateUsageSnapshot, STAGE_KEYS } = await import('../src/usage-dashboard-data.js');
  const operational = Object.fromEntries(STAGE_KEYS.map((stage) => [stage, { runs: 0, errors: 0, skipped: 0, duration_total_ns: 0, duration_max_ns: 0 }]));
  const base = {
    schema_version: 'pathfinder-usage-dashboard-v2', generated_at: '2026-10-19T12:00:00Z',
    window_days: 90, records_seen: 0, rejected_records: 0,
    totals: { jobs: 0, succeeded: 0, failed: 0, aggregate_statuses: { all_aligned: 0, deviations_found: 0, mixed: 0, insufficient_coverage: 0, not_applicable_only: 0, other: 0 }, outcomes: { supported_deviation: 0, no_deviation_found: 0, inconclusive: 0, not_applicable: 0 }, operational_metrics: operational },
    daily: [], model_metering: 'not_metered',
    operational_telemetry: 'not_available',
  };
  assert.throws(() => validateUsageSnapshot({ ...base, schema_version: 'unknown' }));
  assert.throws(() => validateUsageSnapshot({ ...base, totals: { ...base.totals, jobs: -1 } }));
  assert.throws(() => validateUsageSnapshot({ ...base, totals: { ...base.totals, outcomes: { ...base.totals.outcomes, employee_score: 1 } } }));
  assert.throws(() => validateUsageSnapshot({ ...base, totals: { ...base.totals, aggregate_statuses: { ...base.totals.aggregate_statuses, employee_id: 1 } } }));
  assert.throws(() => validateUsageSnapshot({ ...base, daily: Array(92).fill({ date: '2026-10-19', jobs: 0, succeeded: 0, failed: 0, outcomes: base.totals.outcomes }) }));
  assert.throws(() => validateUsageSnapshot({ ...base, generated_at: '2099-01-01T00:00:00Z' }));
  assert.throws(() => validateUsageSnapshot({ ...base, window_days: 1, daily: [{ date: '2026-10-01', jobs: 0, succeeded: 0, failed: 0, aggregate_statuses: base.totals.aggregate_statuses, outcomes: base.totals.outcomes }] }));
});

test('keeps the previous aggregate readable until a new run adds operational telemetry', async () => {
  const { validateUsageSnapshot, STAGE_KEYS } = await import('../src/usage-dashboard-data.js');
  const statuses = { all_aligned: 1, deviations_found: 0, mixed: 0, insufficient_coverage: 0, not_applicable_only: 0, other: 0 };
  const outcomes = { supported_deviation: 0, no_deviation_found: 2, inconclusive: 0, not_applicable: 0 };
  const legacy = validateUsageSnapshot({
    schema_version: 'pathfinder-usage-dashboard-v1', generated_at: '2026-10-19T12:00:00Z', window_days: 90,
    records_seen: 1, rejected_records: 0, model_metering: 'not_metered',
    totals: { jobs: 1, succeeded: 1, failed: 0, aggregate_statuses: statuses, outcomes },
    daily: [{ date: '2026-10-19', jobs: 1, succeeded: 1, failed: 0, aggregate_statuses: statuses, outcomes }],
  });
  assert.equal(legacy.totals.jobs, 1);
  assert.equal(legacy.operational_telemetry, 'not_available');
  assert.equal(legacy.totals.operational_metrics[STAGE_KEYS[0]].runs, 0);
});

test('queries the selected stage and date window from daily aggregates', async () => {
  const { aggregateStageMetrics, STAGE_KEYS } = await import('../src/usage-dashboard-data.js');
  const makeMetrics = (runs, duration) => Object.fromEntries(STAGE_KEYS.map((stage) => [stage, {
    runs: stage === 'evaluation' ? runs : 0, errors: 0, skipped: 0,
    duration_total_ns: stage === 'evaluation' ? duration : 0,
    duration_max_ns: stage === 'evaluation' ? duration : 0,
  }]));
  const days = [
    { date: '2026-10-18', operational_metrics: makeMetrics(2, 4000000) },
    { date: '2026-10-19', operational_metrics: makeMetrics(1, 3000000) },
  ];
  const result = aggregateStageMetrics(days, '2026-10-19T12:00:00Z', 1, 'evaluation');
  assert.equal(result.activeDays, 1);
  assert.equal(result.rows.length, 1);
  assert.equal(result.rows[0].runs, 1);
  assert.equal(result.rows[0].duration_total_ns, 3000000);
  assert.throws(() => aggregateStageMetrics(days, '2026-10-19T12:00:00Z', 7, 'untrusted-label'));
});
