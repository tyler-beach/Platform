const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');

test('usage dashboard is routable and refreshes only its same-origin aggregate snapshot', () => {
  const site = read('src/site.jsx');
  const component = read('src/components/UsageDashboard.jsx');
  const data = read('src/usage-dashboard-data.js');
  assert.match(site, /to="\/usage"/);
  assert.match(site, /path="\/usage\/\*"/);
  assert.match(component, /const REFRESH_MS = 5 \* 60 \* 1000/);
  assert.match(component, /cache: 'no-store'/);
  assert.match(component, /No dashboard snapshot is available yet/);
  assert.match(component, /more than 24 hours old/);
  assert.match(component, /Not metered in this PoC/);
  assert.match(component, /Partial alignment/);
  assert.match(component, /Open Pathfinder workflow/);
  assert.match(component, /Stage performance and errors/);
  assert.match(component, /Mean duration/);
  assert.match(component, /snapshot\.operational_telemetry === 'available'/);
  assert.match(component, /snapshot\?\.records_seen === 0/);
  assert.match(component, /No alignment or deviation conclusion can be drawn/);
  assert.match(component, /aggregateStageMetrics/);
  assert.match(component, /Time range<select/);
  assert.match(component, /Stage<select/);
  assert.match(component, /usageSnapshotURL\(import\.meta\.env\.BASE_URL/);
  assert.match(data, /export function usageSnapshotURL\(basePath/);
  assert.doesNotMatch(data, /raw\.githubusercontent\.com/);
  assert.doesNotMatch(component, /issues\.create|Authorization:|GITHUB_TOKEN/);
});
