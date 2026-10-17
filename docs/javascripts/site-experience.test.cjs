const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const app = fs.readFileSync(path.join(root, 'src/site.jsx'), 'utf8');
const demo = fs.readFileSync(path.join(root, 'src/components/DemoExplorer.jsx'), 'utf8');
const css = fs.readFileSync(path.join(root, 'src/styles.css'), 'utf8');
const build = fs.readFileSync(path.join(root, 'vite.config.js'), 'utf8');
const packageJson = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));

test('public application is React/Vite with first-class Architecture and Demo routes', () => {
  assert.ok(packageJson.dependencies.react);
  assert.ok(packageJson.devDependencies.vite);
  assert.match(build, /outDir:\s*'site'/);
  assert.match(app, /path="\/architecture\/\*"/);
  assert.match(app, /path="\/demo\/\*"/);
  assert.match(app, /Architecture, made inspectable/);
  assert.match(app, /Understand the system/);
  assert.match(app, /Keep decisions on the/);
  assert.match(app, /Follow a paved path/);
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
