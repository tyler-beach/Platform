const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const homepage = fs.readFileSync(path.join(root, 'docs/index.md'), 'utf8');
const demoPage = fs.readFileSync(path.join(root, 'docs/demo/index.md'), 'utf8');
const css = fs.readFileSync(path.join(root, 'docs/stylesheets/extra.css'), 'utf8');
const nav = fs.readFileSync(path.join(root, 'mkdocs.yml'), 'utf8');

test('home page offers distinct Architecture and Demo destinations', () => {
  assert.match(homepage, /href="\.\/system-architecture\/"/);
  assert.match(homepage, /href="\.\/demo\/"/);
  assert.match(nav, /Architecture:/);
  assert.match(nav, /Interactive workflow explorer: demo\/index\.md/);
  assert.match(demoPage, /class="demo-page"/);
});

test('responsive layouts constrain arbitrary data and source panes', () => {
  assert.match(css, /\.demo-page[\s\S]*overflow-wrap:\s*anywhere/);
  assert.match(css, /\.demo-page[\s\S]*min-width:\s*0/);
  assert.match(css, /\.demo-page[\s\S]*pre[\s\S]*overflow-x:\s*auto/);
  assert.match(css, /@media\s*\([^)]*max-width/);
});

test('decorative motion respects reduced-motion preference', () => {
  assert.match(css, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  assert.match(css, /prefers-reduced-motion:\s*reduce[\s\S]*animation-duration:\s*0\.01ms/);
});
