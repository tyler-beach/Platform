import fs from 'node:fs/promises';
import path from 'node:path';

const source = path.resolve('docs/assets');
const destination = path.resolve('public/content/assets');
await fs.rm(destination, { recursive: true, force: true });
await fs.mkdir(path.dirname(destination), { recursive: true });
await fs.cp(source, destination, { recursive: true });
await fs.copyFile('docs/openapi.yaml', 'public/content/openapi.yaml');
console.log('Copied reference assets and OpenAPI source into the static content bundle.');
