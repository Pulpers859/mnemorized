// ══════════════════════════════════════════════════
// FORGE AUTH — auth state, palace persistence, library sidebar
// Depends on: forge-state.js, palace-api.js
// ══════════════════════════════════════════════════

const appConfig = {
  authEnabled: false,
  supabaseUrl: '',
  supabaseAnonKey: '',
  appBaseUrl: ''
};

let supabaseClient = null;
let authState = { session: null, user: null };
let currentPalaceMeta = null;
let currentStoryData = null;
let currentPromptData = { prompt1: '', prompt2: '' };
let libraryRowsCache = [];
const palaceIdFromRoute = new URLSearchParams(window.location.search).get('palace');
let palaceRouteHydrated = false;

function getAuthToken() {
  const token = authState.session?.access_token;
  if (!token) throw new Error('Sign in to access saved palaces.');
  return token;
}

function getActiveToneValue() {
  return document.querySelector('#tone-chips .chip.active')?.dataset.val || 'visceral and cinematic';
}

function setActiveToneValue(value) {
  let matched = false;
  document.querySelectorAll('#tone-chips .chip').forEach(chip => {
    const isMatch = chip.dataset.val === value;
    chip.classList.toggle('active', isMatch);
    if (isMatch) matched = true;
  });
  if (!matched) {
    const first = document.querySelector('#tone-chips .chip');
    if (first) first.classList.add('active');
  }
}

function getDefaultPalaceTitle() {
  const typed = document.getElementById('palace-title-input')?.value?.trim();
  if (typed) return typed;
  if (currentStoryData?.scene_title) return currentStoryData.scene_title;
  const topic = document.getElementById('topic')?.value?.trim() || '';
  const firstLine = topic.split('\n').find(Boolean) || 'Untitled palace';
  return firstLine.replace(/^\[(.+?)\]\s*$/, '$1').slice(0, 90);
}

function getCurrentSourceName() {
  return uploadedFileData?.name || currentPalaceMeta?.source_name || null;
}

function hasSavablePalace() {
  return !!(currentStoryData && currentPromptData.prompt1 && currentPromptData.prompt2);
}

function ensureForgeVisible() {
  document.getElementById('config-divider').style.display = 'flex';
  document.getElementById('config-wrap').style.display = 'block';
  document.getElementById('forge-wrap').style.display = 'block';
  document.getElementById('manual-bypass').style.display = 'none';
}

// ── Account badge ─────────────────────────────────────────────────

function setAccountBadge(mode, label) {
  const btn = document.getElementById('account-btn');
  const status = document.getElementById('account-status');
  status.textContent = label;

  if (mode === 'online') {
    btn.style.color = 'var(--acid)';
    btn.style.borderColor = 'rgba(201,239,77,.3)';
  } else if (mode === 'warning') {
    btn.style.color = 'var(--gold)';
    btn.style.borderColor = 'rgba(245,200,66,.35)';
  } else {
    btn.style.color = 'var(--muted)';
    btn.style.borderColor = 'var(--border)';
  }
}

function setLibraryStatus(message, tone = 'muted') {
  const box = document.getElementById('library-status');
  box.textContent = message;
  if (tone === 'success') {
    box.style.color = 'var(--acid)';
    box.style.borderColor = 'rgba(201,239,77,.25)';
  } else if (tone === 'error') {
    box.style.color = '#fca5a5';
    box.style.borderColor = 'rgba(255,61,61,.25)';
  } else {
    box.style.color = 'var(--muted)';
    box.style.borderColor = 'var(--border)';
  }
}

function setAuthModalStatus(message, tone = 'muted') {
  const el = document.getElementById('auth-modal-status');
  el.textContent = message;
  el.style.color = tone === 'error' ? '#fca5a5' : tone === 'success' ? 'var(--acid)' : 'var(--muted)';
}

function openAuthModal() {
  document.getElementById('auth-modal').style.display = 'flex';
}

function closeAuthModal() {
  document.getElementById('auth-modal').style.display = 'none';
}

document.getElementById('auth-modal').addEventListener('click', function(e) {
  if (e.target === this) closeAuthModal();
});

// ── Palace snapshot ───────────────────────────────────────────────

function buildPalaceSnapshot() {
  return {
    title: getDefaultPalaceTitle(),
    topic: document.getElementById('topic').value.trim(),
    source_name: getCurrentSourceName(),
    scene_title: currentStoryData?.scene_title || '',
    status: 'generated',
    generation_inputs: {
      topic: document.getElementById('topic').value.trim(),
      source_name: getCurrentSourceName(),
      settings: {
        chaos: parseInt(document.getElementById('chaos').value, 10),
        art_style: document.getElementById('style-select').value,
        tone: getActiveToneValue(),
        demo_mode: isDemoMode()
      }
    },
    generation_outputs: {
      story: currentStoryData,
      prompts: {
        prompt1: currentPromptData.prompt1,
        prompt2: currentPromptData.prompt2
      }
    }
  };
}

function renderStoryData(storyData) {
  if (!storyData) return;

  showBody('story');
  document.getElementById('story-header').innerHTML =
    `<div class="story-scene-title">${escapeHtml(storyData.scene_title || '')}</div>
     <div class="story-opening">${escapeHtml(storyData.opening || '')}</div>`;

  document.getElementById('vo-body').innerHTML = (storyData.voLines || []).map(v => `
    <tr>
      <td><span class="row-num">${v.n}</span>${formatNarrationHtml(v.narration)}</td>
      <td>${escapeHtml(v.visual || '')}</td>
      <td class="encodes-cell">${escapeHtml(v.anchor || '')}</td>
    </tr>`).join('');
  document.getElementById('vo-table-wrap').style.display = storyData.voLines?.length ? 'block' : 'none';

  if (storyData.review_script) {
    document.getElementById('review-text').innerHTML = formatReviewBullets(storyData.review_script);
    document.getElementById('review-wrap').style.display = 'block';
  } else {
    document.getElementById('review-wrap').style.display = 'none';
  }
}

function renderPromptData(prompt1, prompt2) {
  showBody('prompt');
  document.getElementById('img-prompt-1').textContent = prompt1 || '';
  document.getElementById('img-prompt-2').textContent = prompt2 || '';
  document.getElementById('prompt-copy-1').value = prompt1 || '';
  document.getElementById('prompt-copy-2').value = prompt2 || '';
}

function setCurrentPalaceData(storyData, prompt1, prompt2) {
  currentStoryData = storyData;
  currentPromptData = {
    prompt1: prompt1 || '',
    prompt2: prompt2 || ''
  };
  refreshAuthUI();
}

// ── Route-based palace loading ────────────────────────────────────

async function maybeLoadRoutePalace() {
  if (!palaceIdFromRoute || palaceRouteHydrated || !authState.user) return;
  palaceRouteHydrated = true;
  await loadPalace(palaceIdFromRoute, { silentScroll: true });
  const url = new URL(window.location.href);
  url.searchParams.delete('palace');
  window.history.replaceState({}, '', url.toString());
}

function applyPalaceSnapshot(palaceRow, versionRow) {
  const inputs = versionRow?.generation_inputs || {};
  const outputs = versionRow?.generation_outputs || {};
  const story = outputs.story || null;
  const prompts = outputs.prompts || {};

  ensureForgeVisible();
  document.getElementById('topic').value = inputs.topic || palaceRow.topic || '';

  if (inputs.settings?.chaos) {
    document.getElementById('chaos').value = String(inputs.settings.chaos);
    updateSlider();
  }
  if (inputs.settings?.art_style) {
    const styleSelect = document.getElementById('style-select');
    const optionExists = [...styleSelect.options].some(option => option.value === inputs.settings.art_style);
    if (optionExists) styleSelect.value = inputs.settings.art_style;
  }
  if (inputs.settings?.tone) setActiveToneValue(inputs.settings.tone);

  document.getElementById('pipeline').classList.add('visible');
  setStatus('story', '✓ Loaded', 'done');
  setStatus('prompt', '✓ Loaded', 'done');

  if (story) renderStoryData(story);
  if (prompts.prompt1 || prompts.prompt2) renderPromptData(prompts.prompt1, prompts.prompt2);

  currentPalaceMeta = palaceRow;
  document.getElementById('palace-title-input').value = palaceRow.title || story?.scene_title || '';
  setCurrentPalaceData(story, prompts.prompt1, prompts.prompt2);
  setLibraryStatus(`Loaded "${palaceRow.title}"`, 'success');
}

// ── Library sidebar ───────────────────────────────────────────────

function renderLibraryRows(rows) {
  libraryRowsCache = rows || [];
  const empty = document.getElementById('library-empty');
  const summary = document.getElementById('library-summary-note');

  if (!rows.length) {
    empty.style.display = 'block';
    empty.textContent = 'No saved palaces yet. Generate one in the forge, then save it and manage it from the library page.';
    summary.textContent = '0 saved palaces. Open Library once you save your first palace.';
    return;
  }

  empty.style.display = 'none';
  const latest = rows[0];
  summary.innerHTML = `${rows.length} saved palace${rows.length === 1 ? '' : 's'} synced. Latest: <span style="color:var(--white)">${escapeHtml(latest.title || 'Untitled palace')}</span> • v${latest.latest_version_number || 1}. Use <a href="/library" style="color:var(--acid);text-decoration:none;">Open Library</a> for search, filters, rename, delete, and load.`;
}

function refreshAuthUI() {
  const openAuthBtn = document.getElementById('open-auth-btn');
  const saveBtn = document.getElementById('save-palace-btn');
  const saveAsNewBtn = document.getElementById('save-as-new-btn');
  const newDraftBtn = document.getElementById('new-draft-btn');
  const refreshBtn = document.getElementById('refresh-library-btn');
  const signOutBtn = document.getElementById('auth-signout-btn');

  if (!appConfig.authEnabled) {
    setAccountBadge('offline', 'AUTH OFF');
    document.getElementById('auth-summary').textContent = 'Backend auth config is missing. Add SUPABASE_URL and SUPABASE_ANON_KEY to turn on accounts and saved palaces.';
    setAuthModalStatus('Set SUPABASE_URL and SUPABASE_ANON_KEY on the backend to enable login.');
    openAuthBtn.textContent = 'Auth Setup';
    saveBtn.disabled = true;
    saveAsNewBtn.disabled = true;
    newDraftBtn.disabled = true;
    refreshBtn.disabled = true;
    signOutBtn.style.display = 'none';
    renderLibraryRows([]);
    setLibraryStatus('Auth disabled until Supabase is configured.');
    return;
  }

  if (authState.user) {
    const label = authState.user.email ? authState.user.email.split('@')[0].slice(0, 12) : 'SIGNED IN';
    setAccountBadge('online', label.toUpperCase());
    document.getElementById('auth-summary').textContent = `Signed in as ${authState.user.email || authState.user.id}. Save from the forge here, then manage the full collection from the dedicated library page.`;
    setAuthModalStatus(`Signed in as ${authState.user.email || authState.user.id}.`);
    openAuthBtn.textContent = 'Account';
    saveBtn.disabled = !hasSavablePalace();
    saveBtn.textContent = currentPalaceMeta?.id ? 'Save Version' : 'Save Palace';
    saveAsNewBtn.disabled = !hasSavablePalace();
    newDraftBtn.disabled = false;
    refreshBtn.disabled = false;
    signOutBtn.style.display = 'block';
    setLibraryStatus(currentPalaceMeta ? `Editing "${currentPalaceMeta.title}"` : 'Library connected.', 'success');
  } else {
    setAccountBadge('warning', 'SIGN IN');
    document.getElementById('auth-summary').textContent = 'Sign in to save palaces, keep a history, and build your personal library.';
    setAuthModalStatus('Create an account or sign in to start saving palaces.');
    openAuthBtn.textContent = 'Sign In';
    saveBtn.disabled = true;
    saveBtn.textContent = 'Save Palace';
    saveAsNewBtn.disabled = true;
    newDraftBtn.disabled = true;
    refreshBtn.disabled = true;
    signOutBtn.style.display = 'none';
    renderLibraryRows([]);
    setLibraryStatus('Sign in to access your library.');
  }
}

function startNewPalaceDraft(fromPalaceId = '') {
  if (!appConfig.authEnabled || !authState.user) {
    openAuthModal();
    return;
  }

  const sourceRow = fromPalaceId ? libraryRowsCache.find(row => row.id === fromPalaceId) : currentPalaceMeta;
  currentPalaceMeta = null;
  if (sourceRow) {
    document.getElementById('palace-title-input').value = `${sourceRow.title} Copy`;
    setLibraryStatus(`Forked "${sourceRow.title}" into a new draft.`, 'success');
  } else {
    document.getElementById('palace-title-input').value = getDefaultPalaceTitle();
    setLibraryStatus('New draft started. The next save will create a new palace.', 'success');
  }
  refreshAuthUI();
  renderLibraryRows(libraryRowsCache);
}

// ── Palace CRUD ───────────────────────────────────────────────────

async function ensureProfileRecord() {
  if (!supabaseClient || !authState.user) return;
  await MnemorizedPalaceApi.ensureProfile(getAuthToken());
}

async function loadLibrary() {
  if (!supabaseClient || !authState.user) {
    refreshAuthUI();
    return;
  }

  setLibraryStatus('Loading library…');
  try {
    const payload = await MnemorizedPalaceApi.list(getAuthToken());
    renderLibraryRows(payload.palaces || []);
    setLibraryStatus(`Loaded ${(payload.palaces || []).length} saved palace${(payload.palaces || []).length === 1 ? '' : 's'}.`, 'success');
    await maybeLoadRoutePalace();
  } catch (error) {
    renderLibraryRows([]);
    setLibraryStatus(`Library load failed: ${error.message}`, 'error');
  }
}

async function deletePalace(palaceId) {
  if (!supabaseClient || !authState.user) {
    openAuthModal();
    return;
  }

  const row = libraryRowsCache.find(item => item.id === palaceId);
  const label = row?.title || 'this palace';
  if (!confirm(`Delete "${label}" and all saved versions? This cannot be undone.`)) {
    return;
  }

  setLibraryStatus(`Deleting "${label}"…`);
  try {
    await MnemorizedPalaceApi.delete(getAuthToken(), palaceId);
  } catch (error) {
    setLibraryStatus(`Delete failed: ${error.message}`, 'error');
    return;
  }

  if (currentPalaceMeta?.id === palaceId) {
    currentPalaceMeta = null;
    refreshAuthUI();
  }

  setLibraryStatus(`Deleted "${label}".`, 'success');
  await loadLibrary();
}

async function loadPalace(palaceId, options = {}) {
  if (!supabaseClient || !authState.user) {
    openAuthModal();
    return;
  }

  setLibraryStatus('Loading palace…');
  let payload;
  try {
    payload = await MnemorizedPalaceApi.load(getAuthToken(), palaceId);
  } catch (error) {
    setLibraryStatus(`Load failed: ${error.message}`, 'error');
    return;
  }

  applyPalaceSnapshot(payload.palace, payload.version);
  if (!options.silentScroll) {
    setTimeout(() => document.getElementById('config-wrap').scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
  }
}

async function saveCurrentPalace(asNew = false) {
  if (!appConfig.authEnabled || !supabaseClient) {
    openAuthModal();
    return;
  }

  if (!authState.user) {
    openAuthModal();
    return;
  }

  if (!hasSavablePalace()) {
    setLibraryStatus('Generate a palace first, then save it.', 'error');
    return;
  }

  const snapshot = buildPalaceSnapshot();
  setLibraryStatus(asNew ? 'Saving new palace…' : 'Saving palace…');

  try {
    const result = await MnemorizedPalaceApi.save(getAuthToken(), {
      palace_id: asNew ? null : currentPalaceMeta?.id || null,
      snapshot
    });
    const palaceRow = result.palace;
    const nextVersion = result.version_number || palaceRow.latest_version_number || 1;

    currentPalaceMeta = palaceRow;
    document.getElementById('palace-title-input').value = palaceRow.title || '';
    setLibraryStatus(`Saved "${palaceRow.title}" as version ${nextVersion}.`, 'success');
    refreshAuthUI();
    await loadLibrary();
  } catch (error) {
    setLibraryStatus(`Save failed: ${error.message}`, 'error');
  }
}

// ── Sign in / up / out ────────────────────────────────────────────

async function signInWithPassword() {
  if (!supabaseClient) {
    setAuthModalStatus('Supabase is not configured yet.', 'error');
    return;
  }

  const email = document.getElementById('auth-email-input').value.trim();
  const password = document.getElementById('auth-password-input').value;
  if (!email || !password) {
    setAuthModalStatus('Enter both email and password.', 'error');
    return;
  }

  setAuthModalStatus('Signing in…');
  try {
    const { data, error } = await runSupabaseQuery(
      'sign in',
      supabaseClient.auth.signInWithPassword({ email, password })
    );
    if (error) {
      setAuthModalStatus(error.message, 'error');
      return;
    }

    authState = { session: data.session, user: data.user };
    refreshAuthUI();
    setAuthModalStatus(`Signed in as ${data.user?.email || email}.`, 'success');

    const results = await Promise.allSettled([ensureProfileRecord(), loadLibrary()]);
    const failed = results.find(result => result.status === 'rejected');
    if (failed) {
      const reason = failed.reason?.message || 'Library sync failed after sign-in.';
      setAuthModalStatus(`Signed in, but follow-up sync failed: ${reason}`, 'error');
    }
  } catch (error) {
    setAuthModalStatus(error.message || 'Sign in failed.', 'error');
  }
}

async function signUpWithPassword() {
  if (!supabaseClient) {
    setAuthModalStatus('Supabase is not configured yet.', 'error');
    return;
  }

  const email = document.getElementById('auth-email-input').value.trim();
  const password = document.getElementById('auth-password-input').value;
  if (!email || !password) {
    setAuthModalStatus('Enter both email and password.', 'error');
    return;
  }

  setAuthModalStatus('Creating account…');
  try {
    const { data, error } = await runSupabaseQuery(
      'sign up',
      supabaseClient.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: getForgeRedirectUrl()
        }
      })
    );
    if (error) {
      setAuthModalStatus(error.message, 'error');
      return;
    }

    authState = { session: data.session, user: data.user };
    refreshAuthUI();

    if (data.user) {
      const results = await Promise.allSettled([ensureProfileRecord(), loadLibrary()]);
      const failed = results.find(result => result.status === 'rejected');
      if (failed) {
        const reason = failed.reason?.message || 'Library sync failed after sign-up.';
        setAuthModalStatus(`Account created, but follow-up sync failed: ${reason}`, 'error');
        return;
      }
    }

    setAuthModalStatus(
      data.session
        ? `Account created and signed in as ${data.user?.email || email}.`
        : 'Account created. Check your email if your Supabase project requires confirmation.',
      'success'
    );
  } catch (error) {
    setAuthModalStatus(error.message || 'Sign up failed.', 'error');
  }
}

async function signOutAccount() {
  if (!supabaseClient) return;
  await supabaseClient.auth.signOut();
  authState = { session: null, user: null };
  currentPalaceMeta = null;
  libraryRowsCache = [];
  refreshAuthUI();
  setAuthModalStatus('Signed out.');
}

// ── Auth system bootstrap ─────────────────────────────────────────

async function loadAuthSystem() {
  try {
    const res = await fetch(getApiUrl('/api/config/public'));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const config = await res.json();
    appConfig.authEnabled = !!config.auth_enabled;
    appConfig.supabaseUrl = config.supabase_url || '';
    appConfig.supabaseAnonKey = config.supabase_anon_key || '';
    appConfig.appBaseUrl = config.app_base_url || window.location.origin;

    if (!appConfig.authEnabled) {
      refreshAuthUI();
      return;
    }

    if (!window.supabase?.createClient) {
      setAuthModalStatus('Supabase client failed to load in the browser.', 'error');
      refreshAuthUI();
      return;
    }

    supabaseClient = window.supabase.createClient(
      appConfig.supabaseUrl,
      appConfig.supabaseAnonKey,
      { auth: { persistSession: true, autoRefreshToken: true } }
    );

    const { data } = await supabaseClient.auth.getSession();
    authState = { session: data.session, user: data.session?.user || null };
    if (authState.user) await ensureProfileRecord();

    supabaseClient.auth.onAuthStateChange(async (_event, session) => {
      authState = { session, user: session?.user || null };
      refreshAuthUI();
      if (authState.user) {
        const results = await Promise.allSettled([ensureProfileRecord(), loadLibrary()]);
        const failed = results.find(result => result.status === 'rejected');
        if (failed) {
          console.error('Auth state sync failed:', failed.reason);
          setLibraryStatus(
            `Signed in, but library sync failed: ${failed.reason?.message || 'Unknown error'}`,
            'error'
          );
        }
      }
    });

    refreshAuthUI();
    if (authState.user) await loadLibrary();
    await maybeLoadRoutePalace();
  } catch (error) {
    appConfig.authEnabled = false;
    supabaseClient = null;
    refreshAuthUI();
    setAuthModalStatus(`Auth config load failed: ${error.message}`, 'error');
  }
}

refreshAuthUI();
loadAuthSystem();
