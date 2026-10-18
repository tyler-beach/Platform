const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const app = fs.readFileSync(path.join(root, 'src/site.jsx'), 'utf8');
const demo = fs.readFileSync(path.join(root, 'src/components/DemoExplorer.jsx'), 'utf8');
const css = fs.readFileSync(path.join(root, 'src/styles.css'), 'utf8');
const flow = fs.readFileSync(path.join(root, 'public/pathfinder-flow/index.html'), 'utf8');
const build = fs.readFileSync(path.join(root, 'vite.config.js'), 'utf8');
const packageJson = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));

test('public application is React/Vite with first-class Architecture and Demo routes', () => {
  assert.ok(packageJson.dependencies.react);
  assert.ok(packageJson.devDependencies.vite);
  assert.match(build, /outDir:\s*'site'/);
  assert.match(app, /path="\/architecture\/\*"/);
  assert.match(app, /path="\/demo\/\*"/);
  assert.match(app, /Understand the system/);
  assert.match(app, /Do the changes follow the rules\?/);
  assert.match(app, /Explore the workflow/);
  assert.match(app, /pathfinder-flow\//);
  assert.match(demo, /demo-gallery-list/);
  assert.match(demo, /demo-stages/);
  assert.match(demo, /demo-run-list/);
});

test('reference Markdown is sanitized and remains linked to checked-in content', () => {
  assert.match(app, /rehypeRaw, rehypeSanitize, rehypeSlug/);
  assert.match(app, /documents\[docPath\]/);
  assert.match(app, /resolveDocumentHref/);
});

test('responsive content stays contained and motion honors reduced-motion', () => {
  assert.match(css, /overflow-wrap:\s*anywhere/);
  assert.match(css, /\.markdown-content pre[\s\S]*overscroll-behavior-inline:\s*contain/);
  assert.match(css, /\.demo-gallery-input pre[\s\S]*overflow/);
  assert.match(css, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  assert.match(css, /@media\s*\(max-width:\s*620px\)/);
});

test('Demo integration loads the existing audited explorer after mount and tears it down', () => {
  assert.match(demo, /ADRDemoLifecycle\?\.init\(\)/);
  assert.match(demo, /ADRDemoLifecycle\?\.destroy\(\)/);
  assert.match(demo, /demo-open-analysis/);
  assert.match(demo, /demo-open-functional/);
});

test('all workflow experiences remain discoverable from the home page', () => {
  assert.match(app, /to="\/demo"/);
  assert.match(app, /to="\/evaluation"/);
  assert.match(app, /pathfinder-flow\//);
  assert.match(app, /MORE TO EXPLORE/);
  assert.match(app, /SIGNAL-FLOW EXPLORER/);
  assert.match(app, /EVALUATION & REPLAY/);
});

test('animated workflow uses one motion system and aligned evidence bus/stages', () => {
  assert.match(flow, /EVIDENCE BUS/);
  assert.match(flow, /M427 143 V522/);
  assert.match(flow, /<div class="stage"><i>03<\/i> Normalize<\/div>/);
  assert.match(flow, /data-node="normalize"/);
  assert.match(flow, /Typed requirement/);
  assert.match(flow, /<div class="stage"><i>07<\/i> Disposition<\/div>/);
  assert.match(flow, /NORMALIZE → COLLECT BY DOMAIN → EVALUATE BY KIND/);
  assert.doesNotMatch(flow, /offset-path:path\(/);
  assert.match(flow, /<animateMotion/);
});

test('home pipeline surfaces normalization on the shared evaluation spine', () => {
  assert.match(app, /Normalize requirement/);
  assert.match(app, /Evaluate by kind/);
  assert.match(app, /SHARED EVALUATION SPINE/);
  assert.match(demo, /Shared evaluation spine/);
  assert.match(demo, /normalize → evaluate/);
});


test('Run Explorer is a separate route backed by live Actions metadata', () => {
  assert.ok(app.includes('path="/explore/*"'));
  assert.ok(app.includes('Run Explorer'));
  const explorer = fs.readFileSync(path.join(root, 'src/components/RunExplorer.jsx'), 'utf8');
  assert.ok(explorer.includes('/actions/runs?per_page=50'));
  assert.ok(explorer.includes('/attempts/${selectedAttempt}/jobs'));
  assert.ok(explorer.includes('STEP INSPECTOR'));
  assert.ok(explorer.includes('Evidence boundary'));
  assert.ok(css.includes('.run-workspace'));
});


test('Run Explorer inspects logs, artifact payloads, attempts, and provenance without inventing step inputs', () => {
  const explorer = fs.readFileSync(path.join(root, 'src/components/RunExplorer.jsx'), 'utf8');
  assert.ok(explorer.includes('/actions/jobs/${selectedStep.jobId}/logs'));
  assert.ok(explorer.includes('/actions/artifacts/${artifact.id}/zip'));
  assert.ok(explorer.includes('/attempts/${selectedAttempt}/jobs'));
  assert.ok(explorer.includes("['evidence','Evidence']"));
  assert.ok(explorer.includes("['inputs','Inputs']"));
  assert.ok(explorer.includes('does not expose resolved shell variables or action inputs'));
  assert.ok(explorer.includes('readZipEntries'));
  assert.ok(explorer.includes('Source commit'));
  assert.ok(css.includes('.run-log-file'));
  assert.ok(css.includes('.run-attempt-picker'));
  assert.ok(explorer.includes('Compare executions'));
  assert.ok(explorer.includes('run-comparison__table'));
  assert.ok(explorer.includes('Faster in selected run'));
  assert.ok(explorer.includes('leftMs < rightMs'));
  assert.ok(explorer.includes('choose another attempt'));
  assert.ok(explorer.includes('Download full file'));
  assert.ok(explorer.includes('visibleStepLogs.map'));
  assert.ok(explorer.includes('Inspect bundle'));
  assert.ok(explorer.includes('run-artifact-files'));
  assert.ok(explorer.includes('File contents match'));
  assert.ok(css.includes('.run-comparison__table'));
  assert.ok(explorer.includes('Recorded workflow inputs'));
  assert.ok(explorer.includes('Pinned source artifacts'));
  assert.ok(explorer.includes('sha256'));
});


test('PoC workflow emits a versioned execution manifest with allowlisted inputs and hashed outputs', () => {
  const workflow = fs.readFileSync(path.join(root, '.github/workflows/poc-analysis.yml'), 'utf8');
  const manifest = fs.readFileSync(path.join(root, '.poc/run_manifest.py'), 'utf8');
  assert.ok(workflow.includes('Write Pathfinder execution manifest'));
  assert.ok(workflow.includes('.poc/run_manifest.py'));
  assert.ok(manifest.includes('pathfinder.execution-manifest/v1'));
  assert.ok(manifest.includes('INPUT_MODEL_PROVIDER'));
  assert.ok(manifest.includes('sha256'));
  assert.ok(manifest.includes('Secret values'));
});
