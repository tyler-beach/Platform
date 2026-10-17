import fs from 'node:fs/promises';
import path from 'node:path';

const site = path.resolve('site');
const index = await fs.readFile(path.join(site, 'index.html'), 'utf8');
const files = await fs.readdir(path.join(site, 'assets'));
const scripts = files.filter((file) => file.endsWith('.js'));
const bundle = (await Promise.all(scripts.map((file) => fs.readFile(path.join(site, 'assets', file), 'utf8')))).join('\n');
for (const marker of ['ADR Platform', 'Architecture', 'Workflow demo', 'demo-explorer', 'scenario-gallery.json', 'sample-run.json', 'Make architectural drift']) {
  if (!bundle.includes(marker)) throw new Error(`Application bundle is missing expected marker: ${marker}`);
}
for (const required of ['site/404.html', 'site/demo/index.html', 'site/openapi.yaml', 'site/content/assets/diagrams/system-architecture.svg']) {
  await fs.access(required);
}
if (!index.includes('id="root"') || !index.includes('type="module"')) throw new Error('Vite React application shell is missing.');
console.log(`Verified React application shell and ${scripts.length} JS bundles, Pages fallbacks, OpenAPI source, and diagram assets.`);
