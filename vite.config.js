import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const repository = process.env.GITHUB_REPOSITORY || 'tyler-beach/Platform';
const safeRepository = /^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9_.-]{1,100}$/.test(repository) ? repository : 'tyler-beach/Platform';

export default defineConfig({
  plugins: [react(), {
    name: 'repository-metadata',
    transformIndexHtml(html) {
      return html.replace('content="tyler-beach/Platform"', `content="${safeRepository}"`);
    },
  }],
  base: process.env.VITE_BASE_PATH || `/${safeRepository.split('/')[1]}/`,
  publicDir: 'public',
  build: { outDir: 'site', emptyOutDir: true, sourcemap: false },
  server: { host: '127.0.0.1' },
});
