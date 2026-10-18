#!/usr/bin/env node
/**
 * Write public/demo-gate.json for the Pages passphrase gate.
 * Reads DEMO_GATE_PASSPHRASE or VITE_DEMO_GATE_PASSPHRASE.
 * When unset/empty, writes { enabled: false }.
 */
import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const passphrase = String(
  process.env.DEMO_GATE_PASSPHRASE
  || process.env.VITE_DEMO_GATE_PASSPHRASE
  || '',
).trim();

const outDir = path.resolve('public');
const outPath = path.join(outDir, 'demo-gate.json');

let payload;
if (!passphrase) {
  payload = {
    schema_version: 'pathfinder-demo-gate-v1',
    enabled: false,
    hash: '',
    note: 'Gate disabled because DEMO_GATE_PASSPHRASE was not set for this build.',
  };
} else {
  payload = {
    schema_version: 'pathfinder-demo-gate-v1',
    enabled: true,
    hash: createHash('sha256').update(passphrase, 'utf8').digest('hex'),
    note: 'Shared passphrase gate enabled. This is scraper friction, not authentication.',
  };
}

await mkdir(outDir, { recursive: true });
await writeFile(outPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({
  ok: true,
  output: outPath,
  enabled: payload.enabled,
}));
