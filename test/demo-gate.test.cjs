const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { pathToFileURL } = require('node:url');

const root = path.resolve(__dirname, '..');

test('demo gate helpers normalize config and match passphrase hashes', async () => {
  const mod = await import(pathToFileURL(path.join(root, 'src/demoGate.js')).href);
  assert.deepEqual(mod.normalizeGateConfig(null), { enabled: false, hash: '' });
  assert.deepEqual(mod.normalizeGateConfig({ enabled: true, hash: 'abc' }), { enabled: false, hash: '' });
  const hash = createHash('sha256').update('demo-secret', 'utf8').digest('hex');
  const enabled = mod.normalizeGateConfig({ enabled: true, hash });
  assert.equal(enabled.enabled, true);
  assert.equal(enabled.hash, hash);
  assert.equal(await mod.passphraseMatches('demo-secret', hash), true);
  assert.equal(await mod.passphraseMatches('wrong', hash), false);

  const memory = {
    store: {},
    getItem(key) { return Object.prototype.hasOwnProperty.call(this.store, key) ? this.store[key] : null; },
    setItem(key, value) { this.store[key] = String(value); },
    removeItem(key) { delete this.store[key]; },
  };
  assert.equal(mod.isSessionUnlocked(memory), false);
  mod.markSessionUnlocked(memory);
  assert.equal(mod.isSessionUnlocked(memory), true);
  mod.clearSessionUnlock(memory);
  assert.equal(mod.isSessionUnlocked(memory), false);
});

test('React shell and pathfinder-flow include the optional demo gate', () => {
  const main = fs.readFileSync(path.join(root, 'src/main.jsx'), 'utf8');
  const gate = fs.readFileSync(path.join(root, 'src/components/DemoGate.jsx'), 'utf8');
  const flow = fs.readFileSync(path.join(root, 'public/pathfinder-flow/index.html'), 'utf8');
  const workflow = fs.readFileSync(path.join(root, '.github/workflows/docs.yml'), 'utf8');
  assert.match(main, /DemoGate/);
  assert.match(gate, /Unlock demo/);
  assert.match(gate, /not real authentication/i);
  assert.match(flow, /demo-flow-gate/);
  assert.match(flow, /demo-gate\.json/);
  assert.match(workflow, /DEMO_GATE_PASSPHRASE/);
});

test('write-demo-gate-config emits disabled config without a passphrase', async () => {
  const { spawnSync } = require('node:child_process');
  const result = spawnSync(process.execPath, ['scripts/write-demo-gate-config.mjs'], {
    cwd: root,
    env: { ...process.env, DEMO_GATE_PASSPHRASE: '', VITE_DEMO_GATE_PASSPHRASE: '' },
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  const config = JSON.parse(fs.readFileSync(path.join(root, 'public/demo-gate.json'), 'utf8'));
  assert.equal(config.enabled, false);
});
