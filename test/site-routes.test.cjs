'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const routes = require('../src/site-routes.cjs');

const docs = [
  'docs/index.md', 'docs/system-architecture.md', 'docs/contracts/EVIDENCE.md',
  'docs/how-to/index.md', 'docs/diagrams/architecture.md', 'docs/api/index.md', 'docs/demo/index.md', 'docs/openapi.yaml',
];

test('legacy MkDocs deep links map to React reference routes', () => {
  assert.equal(routes.resolveLegacyPath('/Platform/system-architecture/', docs, '/Platform/'), '/architecture/system-architecture');
  assert.equal(routes.resolveLegacyPath('/Platform/contracts/EVIDENCE/', docs, '/Platform/'), '/architecture/contracts/evidence');
  assert.equal(routes.resolveLegacyPath('/Platform/api/', docs, '/Platform/'), '/architecture/api/index');
  assert.equal(routes.resolveLegacyPath('/Platform/demo/', docs, '/Platform/'), '/demo');
  assert.equal(routes.resolveLegacyPath('/Platform/openapi.yaml', docs, '/Platform/'), '/architecture/openapi');
  assert.equal(routes.routeForDocument('docs/demo/index.md'), '/demo');
  assert.equal(routes.routeForDocument('docs/openapi.yaml'), '/architecture/openapi');
  assert.equal(routes.resolveLegacyPath('/Platform/not-a-page/', docs, '/Platform/'), null);
});

test('relative Markdown pages and copied assets resolve against the current document', () => {
  assert.equal(routes.resolveDocumentHref('../contracts/EVIDENCE.md#hashes', 'docs/how-to/index.md', docs, '/Platform/'), '/Platform/architecture/contracts/evidence#hashes');
  assert.equal(routes.resolveDocumentHref('../assets/diagrams/system-architecture.svg', 'docs/how-to/index.md', docs, '/Platform/'), '/Platform/content/assets/diagrams/system-architecture.svg');
  assert.equal(routes.resolveDocumentHref('https://example.com/ADR.md', 'docs/index.md', docs, '/Platform/'), 'https://example.com/ADR.md');
  assert.equal(routes.resolveDocumentHref('#overview', 'docs/index.md', docs, '/Platform/'), '#overview');
  assert.equal(routes.resolveDocumentHref('./api/', 'docs/index.md', docs, '/Platform/'), '/Platform/architecture/api/index');
  assert.equal(routes.resolveDocumentHref('./demo/', 'docs/index.md', docs, '/Platform/'), '/Platform/demo');
});
