const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const dashboard = fs.readFileSync(path.join(root, 'src/components/EvaluationDashboard.jsx'), 'utf8');
const site = fs.readFileSync(path.join(root, 'src/site.jsx'), 'utf8');
const styles = fs.readFileSync(path.join(root, 'src/styles.css'), 'utf8');

test('evaluation page keeps three evaluation tracks separate and explicit', () => {
  for (const key of ['regression', 'coverage', 'holdout']) {
    assert.match(dashboard, new RegExp(key));
  }
  assert.match(dashboard, /not independently adjudicated/);
  assert.match(dashboard, /not like-for-like/);
  assert.match(dashboard, /holdout stays quarantined/);
});

test('review lifecycle is navigable and preserves independent adjudication', () => {
  assert.match(dashboard, /Select a review sample/);
  assert.match(dashboard, /Open or reconcile the GitHub Issue/);
  assert.match(dashboard, /Record a disposition/);
  assert.match(dashboard, /Get independent adjudication/);
  assert.match(dashboard, /Export a candidate fixture/);
  assert.match(dashboard, /Compare before promotion/);
  assert.match(dashboard, /onClick=\{\(\) => setStageIndex\(index\)\}/);
});

test('evaluation dashboard is reachable from primary navigation and route', () => {
  assert.match(site, /to="\/evaluation"/);
  assert.match(site, /path="\/evaluation\/\*"/);
  assert.match(dashboard, /pathfinder-scope-review-intake\.yml/);
});

test('dashboard has responsive dark-theme styles', () => {
  assert.match(styles, /\.evaluation-page/);
  assert.match(styles, /\.evaluation-review-loop/);
  assert.match(styles, /@media \(max-width: 760px\)/);
});
