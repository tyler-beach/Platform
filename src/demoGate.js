/** Lightweight shared-passphrase gate helpers for GitHub Pages demos. */

export const DEMO_GATE_STORAGE_KEY = 'pathfinder-demo-gate-unlocked-v1';
export const DEMO_GATE_CONFIG_PATH = 'demo-gate.json';

export function gateConfigUrl(baseUrl = '/') {
  const root = String(baseUrl || '/').endsWith('/') ? baseUrl : `${baseUrl}/`;
  return `${root}${DEMO_GATE_CONFIG_PATH}`;
}

export async function sha256Hex(value) {
  const data = new TextEncoder().encode(String(value ?? ''));
  const digest = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

export function isSessionUnlocked(storage = globalThis.sessionStorage) {
  try {
    return storage?.getItem(DEMO_GATE_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

export function markSessionUnlocked(storage = globalThis.sessionStorage) {
  try {
    storage?.setItem(DEMO_GATE_STORAGE_KEY, '1');
  } catch {
    // Private mode / blocked storage: unlock is in-memory only for this load.
  }
}

export function clearSessionUnlock(storage = globalThis.sessionStorage) {
  try {
    storage?.removeItem(DEMO_GATE_STORAGE_KEY);
  } catch {
    // ignore
  }
}

export function normalizeGateConfig(raw) {
  if (!raw || typeof raw !== 'object') {
    return { enabled: false, hash: '' };
  }
  const hash = typeof raw.hash === 'string' ? raw.hash.trim().toLowerCase() : '';
  const enabled = raw.enabled === true && /^[0-9a-f]{64}$/.test(hash);
  return { enabled, hash: enabled ? hash : '' };
}

export async function loadGateConfig(fetcher = fetch, baseUrl = '/') {
  try {
    const response = await fetcher(gateConfigUrl(baseUrl), { cache: 'no-store' });
    if (!response?.ok) return { enabled: false, hash: '' };
    return normalizeGateConfig(await response.json());
  } catch {
    return { enabled: false, hash: '' };
  }
}

export async function passphraseMatches(passphrase, expectedHash) {
  if (!expectedHash || !/^[0-9a-f]{64}$/i.test(expectedHash)) return false;
  const actual = await sha256Hex(passphrase);
  return actual === expectedHash.toLowerCase();
}
