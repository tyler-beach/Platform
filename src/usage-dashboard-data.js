export const USAGE_SCHEMA = 'pathfinder-usage-dashboard-v2';
const LEGACY_USAGE_SCHEMA = 'pathfinder-usage-dashboard-v1';
export const OUTCOME_KEYS = Object.freeze([
  'supported_deviation',
  'no_deviation_found',
  'inconclusive',
  'not_applicable',
]);
export const AGGREGATE_STATUS_KEYS = Object.freeze([
  'all_aligned', 'deviations_found', 'mixed', 'insufficient_coverage', 'not_applicable_only', 'other',
]);
const MAX_WINDOW_DAYS = 90;
export const STAGE_KEYS = Object.freeze([
  'catalog_load', 'evaluation', 'intake', 'ledger', 'other', 'package_build', 'publication', 'report_write', 'summary',
]);

const isRecord = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const isCount = (value) => Number.isSafeInteger(value) && value >= 0;

function readOutcomeCounts(value) {
  if (!isRecord(value) || Object.keys(value).some((key) => !OUTCOME_KEYS.includes(key))) {
    throw new Error('Dashboard outcomes are invalid.');
  }
  return Object.fromEntries(OUTCOME_KEYS.map((key) => {
    const count = value[key] ?? 0;
    if (!isCount(count)) throw new Error('Dashboard counts are invalid.');
    return [key, count];
  }));
}

function readAggregateStatuses(value) {
  if (!isRecord(value) || Object.keys(value).some((key) => !AGGREGATE_STATUS_KEYS.includes(key))) {
    throw new Error('Dashboard analysis statuses are invalid.');
  }
  return Object.fromEntries(AGGREGATE_STATUS_KEYS.map((key) => {
    const count = value[key] ?? 0;
    if (!isCount(count)) throw new Error('Dashboard analysis counts are invalid.');
    return [key, count];
  }));
}

function readOperationalMetrics(value) {
  if (!isRecord(value) || Object.keys(value).length !== STAGE_KEYS.length || Object.keys(value).some((key) => !STAGE_KEYS.includes(key))) {
    throw new Error('Dashboard operational metrics are invalid.');
  }
  return Object.fromEntries(STAGE_KEYS.map((stage) => {
    const metric = value[stage];
    const fields = ['runs', 'errors', 'skipped', 'duration_total_ns', 'duration_max_ns'];
    if (!isRecord(metric) || Object.keys(metric).some((key) => !fields.includes(key)) || fields.some((key) => !isCount(metric[key]))) {
      throw new Error('Dashboard stage metrics are invalid.');
    }
    if (metric.errors > metric.runs || metric.skipped > metric.runs - metric.errors || metric.duration_max_ns > metric.duration_total_ns || (metric.runs === 0 && fields.slice(1).some((key) => metric[key] !== 0))) {
      throw new Error('Dashboard stage metrics do not reconcile.');
    }
    return [stage, Object.fromEntries(fields.map((key) => [key, metric[key]]))];
  }));
}

function emptyOperationalMetrics() {
  return Object.fromEntries(STAGE_KEYS.map((stage) => [stage, { runs: 0, errors: 0, skipped: 0, duration_total_ns: 0, duration_max_ns: 0 }]));
}

function readCounts(value, legacy = false) {
  if (!isRecord(value)) throw new Error('Dashboard totals are invalid.');
  for (const key of ['jobs', 'succeeded', 'failed']) {
    if (!isCount(value[key])) throw new Error('Dashboard totals are invalid.');
  }
  if (value.succeeded + value.failed !== value.jobs) throw new Error('Dashboard job totals do not reconcile.');
  const counts = {
    jobs: value.jobs,
    succeeded: value.succeeded,
    failed: value.failed,
    aggregate_statuses: readAggregateStatuses(value.aggregate_statuses),
    outcomes: readOutcomeCounts(value.outcomes),
    operational_metrics: legacy && value.operational_metrics === undefined ? emptyOperationalMetrics() : readOperationalMetrics(value.operational_metrics),
  };
  const outcomeTotal = Object.values(counts.outcomes).reduce((sum, count) => sum + count, 0);
  if (!Number.isSafeInteger(outcomeTotal)) throw new Error('Dashboard outcome counts exceed safe limits.');
  const statusTotal = Object.values(counts.aggregate_statuses).reduce((sum, count) => sum + count, 0);
  if (!Number.isSafeInteger(statusTotal) || statusTotal !== counts.succeeded) throw new Error('Dashboard analysis statuses do not reconcile.');
  return counts;
}

export function validateUsageSnapshot(value) {
  if (!isRecord(value) || ![USAGE_SCHEMA, LEGACY_USAGE_SCHEMA].includes(value.schema_version)) throw new Error('Dashboard data version is unsupported.');
  const legacy = value.schema_version === LEGACY_USAGE_SCHEMA;
  const generatedAt = typeof value.generated_at === 'string' ? Date.parse(value.generated_at) : NaN;
  const canonicalGeneratedAt = Number.isFinite(generatedAt) ? new Date(generatedAt).toISOString().replace('.000Z', 'Z') : '';
  if (typeof value.generated_at !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(value.generated_at) || canonicalGeneratedAt !== value.generated_at || generatedAt > Date.now() + 24 * 60 * 60 * 1000) throw new Error('Dashboard freshness is invalid.');
  if (!Number.isSafeInteger(value.window_days) || value.window_days < 1 || value.window_days > MAX_WINDOW_DAYS) throw new Error('Dashboard window is invalid.');
  if (!isCount(value.records_seen) || !isCount(value.rejected_records)) throw new Error('Dashboard record counts are invalid.');
  if (value.model_metering !== 'not_metered') throw new Error('Dashboard metering state is unsupported.');
  if (!legacy && !['available', 'not_available'].includes(value.operational_telemetry)) throw new Error('Dashboard telemetry availability is invalid.');
  if (!Array.isArray(value.daily) || value.daily.length > value.window_days) throw new Error('Dashboard history is invalid.');

  const daily = value.daily.map((item) => {
    if (!isRecord(item) || typeof item.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(item.date)) {
      throw new Error('Dashboard date bucket is invalid.');
    }
    const date = new Date(`${item.date}T00:00:00Z`);
    if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== item.date) throw new Error('Dashboard date bucket is invalid.');
    return { date: item.date, ...readCounts(item, legacy) };
  });
  const totals = readCounts(value.totals, legacy);
  if (new Set(daily.map((item) => item.date)).size !== daily.length) throw new Error('Dashboard dates must be unique.');
  if (daily.some((item, index) => index > 0 && daily[index - 1].date >= item.date)) throw new Error('Dashboard dates must be sorted.');
  const generatedDay = new Date(Date.parse(value.generated_at)).toISOString().slice(0, 10);
  const firstDay = new Date(`${generatedDay}T00:00:00Z`);
  firstDay.setUTCDate(firstDay.getUTCDate() - value.window_days + 1);
  if (daily.some((item) => item.date < firstDay.toISOString().slice(0, 10) || item.date > generatedDay)) throw new Error('Dashboard dates are outside the reporting window.');
  const dailyJobs = daily.reduce((sum, item) => sum + item.jobs, 0);
  const dailySucceeded = daily.reduce((sum, item) => sum + item.succeeded, 0);
  const dailyFailed = daily.reduce((sum, item) => sum + item.failed, 0);
  if (![dailyJobs, dailySucceeded, dailyFailed].every(Number.isSafeInteger) || dailyJobs !== totals.jobs || dailySucceeded !== totals.succeeded || dailyFailed !== totals.failed) {
    throw new Error('Dashboard daily totals do not reconcile.');
  }
  for (const key of AGGREGATE_STATUS_KEYS) {
    const sum = daily.reduce((valueSum, item) => valueSum + item.aggregate_statuses[key], 0);
    if (!Number.isSafeInteger(sum) || sum !== totals.aggregate_statuses[key]) throw new Error('Dashboard status totals do not reconcile.');
  }
  for (const key of OUTCOME_KEYS) {
    const sum = daily.reduce((valueSum, item) => valueSum + item.outcomes[key], 0);
    if (!Number.isSafeInteger(sum) || sum !== totals.outcomes[key]) throw new Error('Dashboard outcome totals do not reconcile.');
  }
  for (const stage of STAGE_KEYS) {
    for (const key of ['runs', 'errors', 'skipped', 'duration_total_ns']) {
      const sum = daily.reduce((valueSum, item) => valueSum + item.operational_metrics[stage][key], 0);
      if (!Number.isSafeInteger(sum) || sum !== totals.operational_metrics[stage][key]) throw new Error('Dashboard stage totals do not reconcile.');
    }
    const maximum = Math.max(0, ...daily.map((item) => item.operational_metrics[stage].duration_max_ns));
    if (maximum !== totals.operational_metrics[stage].duration_max_ns) throw new Error('Dashboard stage duration maxima do not reconcile.');
  }

  return {
    schema_version: USAGE_SCHEMA,
    generated_at: value.generated_at,
    window_days: value.window_days,
    records_seen: value.records_seen,
    rejected_records: value.rejected_records,
    totals,
    daily,
    model_metering: 'not_metered',
    operational_telemetry: legacy ? 'not_available' : value.operational_telemetry,
  };
}

export function ratio(numerator, denominator) {
  if (!isCount(numerator) || !isCount(denominator) || denominator === 0) return null;
  return numerator / denominator;
}

export function aggregateStageMetrics(daily, generatedAt, windowDays, selectedStage = 'all') {
  if (!Array.isArray(daily) || !Number.isInteger(windowDays) || windowDays < 1 || windowDays > MAX_WINDOW_DAYS) throw new Error('Stage query is invalid.');
  if (selectedStage !== 'all' && !STAGE_KEYS.includes(selectedStage)) throw new Error('Stage query is invalid.');
  const end = new Date(generatedAt);
  if (!Number.isFinite(end.getTime())) throw new Error('Stage query date is invalid.');
  const start = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate()));
  start.setUTCDate(start.getUTCDate() - windowDays + 1);
  const fromDate = start.toISOString().slice(0, 10);
  const selectedDays = daily.filter((day) => day.date >= fromDate && day.date <= end.toISOString().slice(0, 10));
  const stages = selectedStage === 'all' ? STAGE_KEYS : [selectedStage];
  const rows = stages.map((stage) => {
    const metric = selectedDays.reduce((total, day) => {
      const current = day.operational_metrics[stage];
      total.runs += current.runs;
      total.errors += current.errors;
      total.skipped += current.skipped;
      total.duration_total_ns += current.duration_total_ns;
      total.duration_max_ns = Math.max(total.duration_max_ns, current.duration_max_ns);
      return total;
    }, { runs: 0, errors: 0, skipped: 0, duration_total_ns: 0, duration_max_ns: 0 });
    return { stage, ...metric };
  });
  return { activeDays: selectedDays.length, rows };
}

export function usageSnapshotURL(basePath = '/') {
  if (typeof basePath !== 'string' || !basePath.startsWith('/') || basePath.startsWith('//') || /[?#\\]/.test(basePath)) return null;
  const segments = basePath.split('/').filter(Boolean);
  if (segments.some((segment) => segment === '.' || segment === '..')) return null;
  const prefix = segments.length ? `/${segments.join('/')}/` : '/';
  return `${prefix}data/summary.json`;
}
