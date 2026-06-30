// ══════════════════════════════════════════════════
// FORGE STATE — shared globals, backend connection, UI helpers
// Loaded first. All other forge-*.js files depend on this.
// ══════════════════════════════════════════════════

const { getApiUrl, escapeHtml, runSupabaseQuery } = MnemorizedUtils;
const CLAUDE_MODEL = 'claude-sonnet-4-6';

let backendState = { checked: false, reachable: false, configured: false, geminiConfigured: false, providerAuthReady: true };

function getBackendBaseLabel() {
  return MnemorizedUtils.getApiBase() || window.location.origin;
}

function getForgeRedirectUrl() {
  const baseUrl = (appConfig.appBaseUrl || window.location.origin || '').replace(/\/+$/, '');
  return `${baseUrl}/forge`;
}

// ── Backend connection UI ─────────────────────────────────────────

function syncConnectionModal(detail) {
  document.getElementById('backend-endpoint-label').textContent = getBackendBaseLabel();
  if (detail) document.getElementById('backend-health-detail').textContent = detail;
}

function setBackendBadge(mode, label) {
  const btn = document.getElementById('backend-btn');
  const status = document.getElementById('backend-status');
  status.textContent = label;

  if (mode === 'online') {
    btn.style.color = 'var(--acid)';
    btn.style.borderColor = 'rgba(201,239,77,.3)';
  } else if (mode === 'warning') {
    btn.style.color = 'var(--gold)';
    btn.style.borderColor = 'rgba(245,200,66,.35)';
  } else {
    btn.style.color = 'var(--red)';
    btn.style.borderColor = 'rgba(255,61,61,.3)';
  }
}

async function refreshBackendStatus(showModalOnError = false) {
  try {
    const res = await fetch(getApiUrl('/api/health'));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    backendState = {
      checked: true,
      reachable: true,
      configured: !!data.anthropic_configured,
      geminiConfigured: !!data.gemini_configured,
      providerAuthReady: !!data.provider_auth_ready
    };

    if (!backendState.providerAuthReady) {
      setBackendBadge('warning', '⚠ AUTH SETUP');
      syncConnectionModal('Provider calls require Supabase auth, but backend auth is not configured yet.');
    } else if (backendState.configured) {
      setBackendBadge('online', '✓ PROXY LIVE');
      syncConnectionModal('Backend reachable and Anthropic is configured server-side.');
    } else {
      setBackendBadge('warning', '⚠ KEY MISSING');
      syncConnectionModal('Backend reachable, but ANTHROPIC_API_KEY is not configured on the server yet.');
    }
  } catch (err) {
    backendState = {
      checked: true,
      reachable: false,
      configured: false,
      geminiConfigured: false,
      providerAuthReady: false
    };
    setBackendBadge('offline', '⚠ PROXY OFFLINE');
    syncConnectionModal(`Could not reach ${getApiUrl('/api/health')}. Start the backend and retry.`);
    if (showModalOnError) openConnectionModal();
  }

  return backendState;
}

function openConnectionModal() {
  syncConnectionModal(document.getElementById('backend-health-detail').textContent);
  document.getElementById('connection-modal').style.display = 'flex';
}

function closeConnectionModal() {
  document.getElementById('connection-modal').style.display = 'none';
}

async function retryConnection() {
  const btn = document.getElementById('retry-backend-btn');
  btn.disabled = true;
  btn.textContent = 'Checking…';
  await refreshBackendStatus(true);
  btn.disabled = false;
  btn.textContent = 'Retry Connection';
}

document.getElementById('connection-modal').addEventListener('click', function(e) {
  if (e.target === this) closeConnectionModal();
});

// ── Claude API fetch wrapper ──────────────────────────────────────

async function claudeFetch(body) {
  if (!backendState.checked) await refreshBackendStatus();

  if (!backendState.reachable) {
    openConnectionModal();
    throw new Error(`Proxy unavailable. Start the backend at ${getBackendBaseLabel()} and retry.`);
  }

  if (!backendState.configured) {
    openConnectionModal();
    throw new Error('Backend is reachable, but ANTHROPIC_API_KEY is not configured on the server.');
  }

  if (!backendState.providerAuthReady) {
    openConnectionModal();
    throw new Error('Provider calls require Supabase auth, but backend auth is not configured yet.');
  }

  const headers = {
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01'
  };
  if (authState.session?.access_token) {
    headers.Authorization = `Bearer ${authState.session.access_token}`;
  }

  let res;
  try {
    res = await fetch(getApiUrl('/api/anthropic/messages'), {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    });
  } catch (err) {
    backendState = { checked: true, reachable: false, configured: false, geminiConfigured: false, providerAuthReady: false };
    setBackendBadge('offline', '⚠ PROXY OFFLINE');
    syncConnectionModal(`Could not reach ${getApiUrl('/api/anthropic/messages')}. Start the backend and retry.`);
    openConnectionModal();
    throw new Error(`Proxy unavailable: ${err.message}`);
  }

  if (res.status === 401) {
    openAuthModal();
    throw new Error('Sign in to use the API proxy.');
  } else if (res.status === 402) {
    const quota = await res.json().catch(() => ({}));
    const used = quota.usage?.used ?? '?';
    const limit = quota.usage?.limit ?? '?';
    throw new Error(`Monthly quota exceeded (${used}/${limit} requests). Upgrade your plan or wait for the next billing period.`);
  } else if (res.status === 503) {
    const payload = await res.clone().json().catch(() => ({}));
    backendState.configured = false;
    setBackendBadge('warning', '⚠ KEY MISSING');
    syncConnectionModal(payload.error?.message || 'Backend reached the proxy, but a required provider key or auth setting is missing.');
  } else if (res.ok) {
    backendState = { checked: true, reachable: true, configured: true, geminiConfigured: backendState.geminiConfigured, providerAuthReady: backendState.providerAuthReady };
    setBackendBadge('online', '✓ PROXY LIVE');
  }

  return res;
}

refreshBackendStatus();

// ── Generic UI helpers ────────────────────────────────────────────

function setStatus(id, text, cls) {
  const el = document.getElementById('status-' + id);
  el.textContent = text;
  el.className = 'stage-status ' + (cls || '');
}

function showBody(id) {
  document.getElementById('body-' + id).style.display = 'block';
}

function copyToClipboard(text, btn, label) {
  const done = () => {
    btn.textContent = '✓ Copied!'; btn.classList.add('copied');
    setTimeout(() => { btn.textContent = label; btn.classList.remove('copied'); }, 2000);
  };
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
  } else {
    fallbackCopy(text, done);
  }
}

function fallbackCopy(text, done) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0;';
  document.body.appendChild(ta);
  ta.focus(); ta.select();
  try { document.execCommand('copy'); done(); } catch(e) { alert('Copy failed — please select and copy manually.'); }
  document.body.removeChild(ta);
}

function formatNarrationHtml(text) {
  return escapeHtml(text)
    .replace(/\[PAUSE\]/gi, '<span class="cue-pause">[pause]</span>')
    .replace(/\[BEAT\]/gi, '<span class="cue-pause">[beat]</span>')
    .replace(/\[EMPHASIS:\s*([^\]]+)\]/gi, '<span class="cue-em">$1</span>');
}

function formatReviewBullets(text) {
  const lines = String(text || '').split('\n').map(l => l.trim()).filter(Boolean);
  if (lines.length <= 1) return `<ul><li>${escapeHtml(text)}</li></ul>`;
  return '<ul>' + lines.map(l => `<li>${escapeHtml(l)}</li>`).join('') + '</ul>';
}
