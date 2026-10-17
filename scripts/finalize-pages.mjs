import fs from 'node:fs/promises';
import path from 'node:path';

const index = await fs.readFile('site/index.html');
await fs.writeFile('site/404.html', index);
await fs.mkdir('site/demo', { recursive: true });
await fs.writeFile('site/demo/index.html', index);
await fs.copyFile('docs/openapi.yaml', 'site/openapi.yaml');
console.log('Wrote GitHub Pages deep-link and demo route fallbacks.');
