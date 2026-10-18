import React, { useEffect, useState } from 'react';
import { LockKeyhole, ShieldCheck } from 'lucide-react';
import { BASE_URL } from '../content.js';
import {
  isSessionUnlocked,
  loadGateConfig,
  markSessionUnlocked,
  passphraseMatches,
} from '../demoGate.js';

export default function DemoGate({ children }) {
  const [state, setState] = useState({ status: 'loading', hash: '' });
  const [passphrase, setPassphrase] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const config = await loadGateConfig(fetch, BASE_URL);
      if (cancelled) return;
      if (!config.enabled) {
        setState({ status: 'open', hash: '' });
        return;
      }
      if (isSessionUnlocked()) {
        setState({ status: 'open', hash: config.hash });
        return;
      }
      setState({ status: 'locked', hash: config.hash });
    })();
    return () => { cancelled = true; };
  }, []);

  async function onSubmit(event) {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      const ok = await passphraseMatches(passphrase, state.hash);
      if (!ok) {
        setError('Passphrase did not match.');
        return;
      }
      markSessionUnlocked();
      setState((current) => ({ ...current, status: 'open' }));
    } finally {
      setBusy(false);
    }
  }

  if (state.status === 'loading') {
    return <div className="demo-gate" role="status"><p className="demo-gate__muted">Checking demo access…</p></div>;
  }

  if (state.status === 'open') return children;

  return <div className="demo-gate">
    <form className="demo-gate__card" onSubmit={onSubmit}>
      <div className="demo-gate__icon" aria-hidden="true"><LockKeyhole size={22} /></div>
      <h1>Demo access</h1>
      <p>Enter the shared passphrase to browse the Pathfinder demo. This is lightweight friction for scrapers—not real authentication.</p>
      <label className="demo-gate__field">
        <span>Passphrase</span>
        <input
          type="password"
          autoComplete="current-password"
          value={passphrase}
          onChange={(event) => setPassphrase(event.target.value)}
          disabled={busy}
          required
        />
      </label>
      {error ? <p className="demo-gate__error" role="alert">{error}</p> : null}
      <button type="submit" className="demo-gate__submit" disabled={busy || !passphrase}>
        {busy ? 'Checking…' : 'Unlock demo'}
      </button>
      <p className="demo-gate__note"><ShieldCheck size={14} /> GitHub Issues and Actions remain separate from this page gate.</p>
    </form>
  </div>;
}
