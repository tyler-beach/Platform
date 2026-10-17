import fs from 'node:fs/promises';
import path from 'node:path';

async function listMarkdown(directory, prefix = '') {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    const relative = path.posix.join(prefix, entry.name);
    if (entry.isDirectory()) files.push(...await listMarkdown(path.join(directory, entry.name), relative));
    else if (entry.isFile() && entry.name.toLowerCase().endsWith('.md')) files.push(relative);
  }
  return files;
}

const paths = await listMarkdown('docs');
const manifest = [];
for (const docPath of paths) {
  let source = await fs.readFile(path.join('docs', docPath), 'utf8');
  source = source.replace(/^---\s*\n[\s\S]*?\n---\s*\n/, '');
  const title = source.match(/^#\s+(.+)$/m)?.[1]?.replace(/[*_`]/g, '').trim() || path.basename(docPath, '.md').replace(/[-_]/g, ' ');
  const paragraph = source.split(/\n\s*\n/).map((part) => part.replace(/\s+/g, ' ').trim()).find((part) => part && !part.startsWith('#') && !part.startsWith('![') && !part.startsWith('<')) || '';
  manifest.push({ path: docPath, title, summary: paragraph.slice(0, 180) });
}
await fs.writeFile('src/generated-doc-index.json', `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`Indexed ${manifest.length} Markdown reference documents.`);
