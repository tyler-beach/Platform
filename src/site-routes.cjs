'use strict';

function cleanDocKey(value) {
  return String(value || '')
    .replace(/^\/?(?:docs\/)?/i, '')
    .replace(/\\/g, '/')
    .replace(/\.md$/i, '')
    .replace(/\/+$/, '')
    .toLowerCase();
}

function routeForDocument(docPath) {
  const key = cleanDocKey(docPath);
  if (!key || key === 'index') return '/architecture';
  if (key === 'demo/index') return '/demo';
  if (key === 'openapi.yaml') return '/architecture/openapi';
  return `/architecture/${key}`;
}

function matchDocPath(path, documents) {
  const key = cleanDocKey(path);
  if (!key) return documents.find((item) => cleanDocKey(item) === 'index.md') || null;
  const direct = documents.find((item) => cleanDocKey(item) === key);
  if (direct) return direct;
  const indexPage = documents.find((item) => cleanDocKey(item) === `${key}/index`);
  if (indexPage) return indexPage;
  return documents.find((item) => cleanDocKey(item).split('/').at(-1) === key) || null;
}

function resolveLegacyPath(pathname, documents, basePath = '/') {
  let path = String(pathname || '/');
  const base = `/${String(basePath || '/').split('/').filter(Boolean).join('/')}`;
  if (base !== '/' && path.startsWith(`${base}/`)) path = path.slice(base.length);
  path = path.replace(/^\/+|\/+$/g, '');
  if (!path || path.toLowerCase() === 'index.html') return '/';
  if (path.toLowerCase() === 'architecture') return '/architecture';
  if (path.toLowerCase() === 'demo') return '/demo';
  if (path.toLowerCase() === 'openapi' || path.toLowerCase() === 'openapi.yaml') return '/architecture/openapi';
  if (path.toLowerCase().startsWith('architecture/')) {
    const doc = matchDocPath(path.slice('architecture/'.length), documents);
    return doc ? routeForDocument(doc) : null;
  }
  const doc = matchDocPath(path, documents);
  return doc ? routeForDocument(doc) : null;
}

function resolveDocumentHref(href, currentDoc, documents, baseUrl = '/') {
  if (typeof href !== 'string' || !href.trim()) return href;
  if (/^(?:[a-z][a-z\d+.-]*:|\/\/|mailto:|tel:)/i.test(href) || href.startsWith('#')) return href;
  const current = String(currentDoc || '').replace(/^docs\//, '');
  const currentDir = current.includes('/') ? current.slice(0, current.lastIndexOf('/') + 1) : '';
  let url;
  try { url = new URL(href, `https://local.invalid/${currentDir}`); } catch (_) { return href; }
  if (url.origin !== 'https://local.invalid') return href;
  const target = decodeURIComponent(url.pathname).replace(/^\//, '');
  const dot = target.lastIndexOf('.');
  const ext = dot >= 0 ? target.slice(dot + 1).toLowerCase() : '';
  if (ext === 'md' || !ext) {
    const doc = matchDocPath(target, documents);
    if (doc) return `${baseUrl.replace(/\/$/, '')}${routeForDocument(doc)}${url.search}${url.hash}`;
  }
  if (['svg', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'yaml', 'yml', 'json'].includes(ext)) {
    return `${baseUrl.replace(/\/$/, '')}/content/${target}${url.search}${url.hash}`;
  }
  return href;
}

module.exports = { cleanDocKey, routeForDocument, matchDocPath, resolveLegacyPath, resolveDocumentHref };
