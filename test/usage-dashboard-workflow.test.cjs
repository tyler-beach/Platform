const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workflow = fs.readFileSync('.github/workflows/pathfinder-go-analyze.yml', 'utf8');
const caller = fs.readFileSync('.github/workflows/pathfinder-issue-analyze.yml', 'utf8');
const pagesWorkflow = fs.readFileSync('.github/workflows/docs.yml', 'utf8');
const refreshWorkflow = fs.readFileSync('.github/workflows/pathfinder-pages-refresh.yml', 'utf8');
const pagesPublisher = fs.readFileSync('scripts/prepare-pathfinder-pages-data.py', 'utf8');

test('analysis exports optional OTel and updates the projection with the serialized ledger write', () => {
  assert.match(workflow, /OTEL_EXPORTER_OTLP_ENDPOINT:\s*\$\{\{ vars\.OTEL_EXPORTER_OTLP_ENDPOINT \}\}/);
  assert.match(workflow, /OTEL_EXPORTER_OTLP_HEADERS:\s*\$\{\{ secrets\.OTEL_EXPORTER_OTLP_HEADERS \}\}/);
  assert.match(workflow, /group: pathfinder-jobs-ledger/);
  assert.match(workflow, /permissions:\n  contents: read\n  issues: write/);
  assert.match(workflow, /ledger:[\s\S]*?permissions:\n      contents: write/);
  assert.match(workflow, /pathfinder-dashboard-summary[\s\S]*?--input[\s\S]*?jobs\/jobs\.jsonl[\s\S]*?--output[\s\S]*?dashboard\/summary\.json/);
  assert.match(workflow, /add jobs\/jobs\.jsonl dashboard\/summary\.json/);
  assert.match(workflow, /continue-on-error: true[\s\S]*?Ledger append failed after \$max_attempts attempts/);
  assert.match(workflow, /Soft-fail note when ledger failed[\s\S]*?::warning::pathfinder-jobs ledger append failed/);
  assert.match(caller, /resolve:[\s\S]*?permissions:\n      contents: read\n      issues: read/);
  assert.match(caller, /analyze:[\s\S]*?permissions:\n      contents: write\n      issues: write/);
  assert.match(workflow, /Upload stage artifacts[\s\S]*?if: always\s*[\s\S]*?pathfinder-issue-evaluation-/);
  const issueAnalyzer = fs.readFileSync('go/pathfinder/cmd/pathfinder-issue-analyze/main.go', 'utf8');
  assert.match(issueAnalyzer, /BuildWithTelemetry[\s\S]*?StageSnapshot\(\)/);
  assert.match(workflow, /pathfinder-issue\/job\.json/);
  assert.match(refreshWorkflow, /Pathfinder Issue Package Evaluation/);
  assert.match(refreshWorkflow, /Require the source run's Pathfinder evaluation artifact/);
  assert.match(refreshWorkflow, /pathfinder-issue-evaluation-\$\{SOURCE_RUN_ID\}-\$\{SOURCE_RUN_ATTEMPT\}/);
  assert.match(refreshWorkflow, /ref: pathfinder-pages/);
  assert.match(refreshWorkflow, /needs: gate/);
  assert.match(refreshWorkflow, /Upload the saved site as a Pages artifact/);
  assert.match(refreshWorkflow, /Deploy refreshed dashboard data/);
  assert.doesNotMatch(refreshWorkflow, /npm ci|npm run build|go run|unittest discover/);
  assert.doesNotMatch(pagesWorkflow, /Pathfinder Issue Package Evaluation/);
  assert.match(pagesWorkflow, /Save deployable site bundle for data-only refreshes/);
  assert.ok(pagesWorkflow.includes('group: github-pages-${{ github.repository }}'));
  assert.match(pagesWorkflow, /cancel-in-progress: false/);
  assert.match(pagesWorkflow, /site\/data\/summary\.json/);
  assert.match(pagesWorkflow, /empty-summary\.json/);
  assert.match(pagesWorkflow, /cp "\$DEST_DIR\/data\/empty-summary\.json" "\$DEST_DIR\/data\/summary\.json"/);
  assert.match(pagesWorkflow, /pages-site-\$\{\{ github\.run_id \}\}-\$\{\{ github\.run_attempt \}\}/);
  assert.match(pagesWorkflow, /pathfinder-pages/);
  assert.match(pagesPublisher, /pages\.get\("public"\) is not False/);
  assert.match(pagesPublisher, /get\("visibility"\) != "private"/);
  assert.match(pagesWorkflow, /data\/summary\.json/);
  assert.doesNotMatch(pagesWorkflow, /raw\.githubusercontent\.com/);
});

test('Pages snapshot publisher fails closed and embeds a verified private aggregate', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'pathfinder-pages-'));
  const script = path.resolve('scripts/prepare-pathfinder-pages-data.py');
  const output = path.join(directory, 'summary.json');
  const summary = {
    schema_version: 'pathfinder-usage-dashboard-v2', generated_at: '2026-10-19T12:00:00Z',
    window_days: 90, records_seen: 0, rejected_records: 0, totals: {}, daily: [],
    model_metering: 'not_metered', operational_telemetry: 'not_available',
  };
  const repository = path.join(directory, 'repo.json');
  const pages = path.join(directory, 'pages.json');
  const contents = path.join(directory, 'contents.json');
  fs.writeFileSync(repository, JSON.stringify({ visibility: 'private', owner: { type: 'Organization' } }));
  fs.writeFileSync(pages, JSON.stringify({ public: false }));
  fs.writeFileSync(contents, JSON.stringify({ type: 'file', path: 'dashboard/summary.json', content: Buffer.from(JSON.stringify(summary)).toString('base64') }));
  const run = () => spawnSync('python3', [script, '--repository', repository, '--pages', pages, '--contents', contents, '--output', output], { encoding: 'utf8' });

  fs.writeFileSync(pages, JSON.stringify({ public: true }));
  assert.notEqual(run().status, 0);
  assert.equal(fs.existsSync(output), false);
  fs.writeFileSync(pages, JSON.stringify({ public: false }));
  assert.equal(run().status, 0);
  assert.equal(JSON.parse(fs.readFileSync(output, 'utf8')).schema_version, summary.schema_version);

  summary.run_id = 'must-not-publish';
  fs.writeFileSync(contents, JSON.stringify({ type: 'file', path: 'dashboard/summary.json', content: Buffer.from(JSON.stringify(summary)).toString('base64') }));
  assert.notEqual(run().status, 0);
  fs.rmSync(directory, { recursive: true, force: true });
});
