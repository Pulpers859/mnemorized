// ══════════════════════════════════════════════════
// FORGE AUTH — auth state, palace persistence, library sidebar
// Depends on: forge-state.js, palace-api.js
// ══════════════════════════════════════════════════

const appConfig = {
  authEnabled: false,
  supabaseUrl: '',
  supabaseAnonKey: '',
  appBaseUrl: '',
  demoAuthBypass: false,
  medicalKnowledgeEnabled: false,
  billingMode: 'beta',
  betaMode: true,
  billingEnabled: false,
  upgradeEnabled: false,
  upgradePathEnabled: false,
  billingMessage: 'Mnemorized is in private beta. Billing is not active yet; beta accounts use fixed monthly request limits.',
  quotaUnitLabel: 'AI requests'
};

let supabaseClient = null;
let authState = { session: null, user: null };
let currentPalaceMeta = null;
let currentStoryData = null;
let currentPromptData = { prompt1: '', prompt2: '' };
let currentQualityGateData = null;
let libraryRowsCache = [];
const palaceIdFromRoute = new URLSearchParams(window.location.search).get('palace');
let palaceRouteHydrated = false;
const catalogIdFromRoute = new URLSearchParams(window.location.search).get('catalog');
let catalogRouteHydrated = false;
function getAuthToken() {
  const token = authState.session?.access_token;
  if (!token) throw new Error('Sign in to access saved palaces.');
  return token;
}

function getMedicalAuthToken() {
  const token = authState.session?.access_token;
  if (token) return token;
  if (appConfig.demoAuthBypass) return null;
  throw new Error('Sign in to access saved palaces.');
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
  document.getElementById('config-wrap').style.display = 'block';
  document.getElementById('forge-wrap').style.display = 'block';
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
      quality_gate: currentQualityGateData,
      prompts: {
        prompt1: currentPromptData.prompt1,
        prompt2: currentPromptData.prompt2
      },
      guided_video: window.MnemorizedGuided?.getSnapshot?.() || null
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
      <td><span class="row-num">${v.n}</span>${v.hook ? `<div class="hook-tag">${escapeHtml(v.hook)}</div>` : ''}${formatNarrationHtml(v.narration)}</td>
      <td>${escapeHtml(v.visual || '')}</td>
      <td class="encodes-cell">${escapeHtml(v.anchor || '')}</td>
    </tr>`).join('');
  document.getElementById('vo-table-wrap').style.display = storyData.voLines?.length ? 'block' : 'none';

  if (storyData.review_script) {
    document.getElementById('review-text').innerHTML = formatReviewBullets(storyData.review_script);
    document.getElementById('review-wrap').removeAttribute('open');
    document.getElementById('review-wrap').style.display = 'block';
  } else {
    document.getElementById('review-wrap').style.display = 'none';
  }
}

function getQualityGateConcepts(storyData) {
  return (storyData?.voLines || [])
    .map(line => line.anchor || line.narration || '')
    .map(text => String(text).trim())
    .filter(Boolean)
    .slice(0, 12);
}

function extractXmlTag(text, tag) {
  const re = new RegExp(`<${tag}>[\\s\\S]*?<\\/${tag}>`, 'i');
  const match = String(text || '').match(re);
  if (!match) return '';
  return match[0]
    .replace(new RegExp(`^<${tag}>`, 'i'), '')
    .replace(new RegExp(`<\\/${tag}>$`, 'i'), '')
    .trim();
}

function extractAllXmlTags(text, tag) {
  const re = new RegExp(`<${tag}>[\\s\\S]*?<\\/${tag}>`, 'gi');
  return [...String(text || '').matchAll(re)].map(match =>
    match[0]
      .replace(new RegExp(`^<${tag}>`, 'i'), '')
      .replace(new RegExp(`<\\/${tag}>$`, 'i'), '')
      .trim()
  );
}

function sanitizeVisualField(text) {
  return String(text || '')
    .replace(/[→⇒➜➔]/g, ' beside ')
    .replace(/[←⇐]/g, ' beside ')
    .replace(/[↑⇑]/g, ' above ')
    .replace(/[↓⇓]/g, ' below ')
    .replace(/\s+/g, ' ')
    .trim();
}

function parseProviderContent(raw, context) {
  if (raw.type === 'error' || raw.error) {
    const msg = raw.error?.message || raw.message || JSON.stringify(raw);
    throw new Error(`${context}: ${msg}`);
  }
  if (!raw.content || !Array.isArray(raw.content)) {
    throw new Error(`${context}: unexpected provider response.`);
  }
  const text = raw.content
    .filter(part => part?.type === 'text' && typeof part.text === 'string')
    .map(part => part.text)
    .join('\n')
    .trim();
  if (!text) {
    const contentTypes = raw.content
      .map(part => part?.type || part?.name || 'unknown')
      .filter(Boolean)
      .join(', ');
    if (raw.stop_reason === 'max_tokens') {
      throw new Error(`${context}: provider response hit the max token limit before returning text.`);
    }
    if (contentTypes) {
      throw new Error(`${context}: provider returned no text blocks. Content blocks: ${contentTypes}.`);
    }
    throw new Error(`${context}: empty provider response.`);
  }
  return text;
}

function parseStoryXml(text) {
  const voRaw = extractAllXmlTags(text, 'vo_line');
  const voLines = voRaw.map((block, index) => {
    const getField = (label) => {
      const re = new RegExp(
        `${label}:\\s*\\[?([\\s\\S]*?)\\]?(?=\\n(?:HOOK|NARRATION|VISUAL|ANCHOR):|$)`,
        'i'
      );
      const match = block.match(re);
      if (!match) return '';
      return match[1].replace(/\]?\s*$/, '').trim();
    };
    return {
      n: index + 1,
      hook: getField('HOOK'),
      narration: getField('NARRATION'),
      visual: sanitizeVisualField(getField('VISUAL')),
      anchor: getField('ANCHOR'),
    };
  });

  return {
    scene_title: extractXmlTag(text, 'scene_title'),
    opening: extractXmlTag(text, 'opening'),
    voLines,
    review_script: extractXmlTag(text, 'review_script'),
  };
}

function countWords(text) {
  return String(text || '').trim().split(/\s+/).filter(Boolean).length;
}

function validateStoryData(storyData) {
  const fatal = [];
  const warnings = [];
  const lines = storyData?.voLines || [];
  const hookTypes = /^(sound-alike|look-alike|functional|contrast|spatial)\b/i;

  if (!storyData) {
    fatal.push('Story response was empty.');
    return { fatal, warnings, all: fatal.concat(warnings) };
  }
  if (!storyData.scene_title) warnings.push('Missing scene title.');
  if (!storyData.opening) warnings.push('Missing opening narration.');
  if (!lines.length) fatal.push('No vo_line anchors were returned.');
  if (lines.length && lines.length < 6) warnings.push(`Only ${lines.length} anchors returned; most topics need 8-10.`);
  if (lines.length > 10) fatal.push(`Too many anchors returned (${lines.length}); merge to 8-10 before image generation.`);

  const visualKeys = new Set();
  lines.forEach((line, index) => {
    const label = `Anchor ${index + 1}`;
    if (!line.narration) fatal.push(`${label} is missing NARRATION.`);
    if (!line.visual) fatal.push(`${label} is missing VISUAL.`);
    if (!line.anchor) fatal.push(`${label} is missing ANCHOR.`);
    if (!line.hook) {
      warnings.push(`${label} is missing HOOK; visual cue quality may degrade.`);
    } else if (!hookTypes.test(line.hook)) {
      warnings.push(`${label} HOOK should start with sound-alike, look-alike, functional, contrast, or spatial.`);
    }

    const visualWordCount = countWords(line.visual);
    if (visualWordCount > 34) {
      fatal.push(`${label} visual is ${visualWordCount} words; visual anchors must be 30 words or fewer before image generation.`);
    } else if (visualWordCount > 30) {
      warnings.push(`${label} visual is ${visualWordCount} words; target is 30 or fewer.`);
    }

    const visualText = String(line.visual || '');
    const quotedLabels = visualText.match(/"[^"]+"/g) || [];
    const textSurfaceMarkers = visualText.match(/\b(?:label(?:ed)?|reads?|showing|sign|chalkboard|ribbon|speech bubble|logbook|plaque|stamped|etched|row[s]?:|shows?)\b/gi) || [];
    if (quotedLabels.length > 2 || textSurfaceMarkers.length > 3) {
      fatal.push(`${label} visual depends on too many text surfaces; rebuild it as a silhouette-first object interaction with at most two essential labels.`);
    }
    if (/[→←↑↓]/.test(visualText)) {
      fatal.push(`${label} visual uses arrow glyphs; replace arrows with spatial sequence or plain object relationships.`);
    }
    if (/\bspeech bubble\b/i.test(visualText)) {
      fatal.push(`${label} visual uses a speech bubble; speech bubbles turn the scene into a captioned infographic.`);
    }

    const anchorWordCount = countWords(line.anchor);
    if (anchorWordCount > 35) warnings.push(`${label} anchor is wordy; keep ANCHOR to one crisp clinical fact.`);
    if (/\bget it\b|\bremember\b|\bthis is your\b/i.test(line.anchor || '')) {
      warnings.push(`${label} anchor contains mnemonic/narration language; ANCHOR should be clinical fact only.`);
    }

    const visualKey = String(line.visual || '').toLowerCase().replace(/\s+/g, ' ').trim();
    if (visualKey) {
      if (visualKeys.has(visualKey)) warnings.push(`${label} duplicates a prior visual anchor.`);
      visualKeys.add(visualKey);
    }
  });

  const reviewLines = String(storyData.review_script || '')
    .split(/\n+/)
    .map(line => line.trim())
    .filter(Boolean);
  if (!storyData.review_script) {
    warnings.push('Missing rapid review script.');
  } else if (lines.length && reviewLines.length < lines.length) {
    warnings.push(`Rapid review has ${reviewLines.length} lines for ${lines.length} anchors.`);
  }

  return { fatal, warnings, all: fatal.concat(warnings) };
}

function renderQualityGateMessage(message, tone = 'muted', title = 'Medical Quality Gate') {
  showBody('quality');
  const body = document.getElementById('quality-result');
  const toneClass = tone === 'error' ? 'quality-error' : tone === 'success' ? 'quality-success' : '';
  const verdict = tone === 'error' ? 'Needs attention' : tone === 'success' ? 'Ready' : 'Working';
  body.innerHTML = `<div class="quality-summary ${toneClass}">
    <div class="quality-kicker">${escapeHtml(title)}</div>
    <div class="quality-verdict">${escapeHtml(verdict)}</div>
    <div class="quality-copy">${escapeHtml(message)}</div>
  </div>`;
}

function renderQualityGateResult(result) {
  showBody('quality');
  const evidence = result?.evidence || [];
  const coverage = result?.required_concept_coverage || [];
  const presentCount = coverage.filter(item => item.present_in_generation).length;
  const coverageLabel = coverage.length ? `${presentCount}/${coverage.length} contract concepts covered` : 'No required anchors were supplied.';
  const hasRelevantEvidence = result?.evidence_status !== 'no_relevant_source';
  const evidenceLabel = hasRelevantEvidence
    ? `${evidence.length} private evidence citation${evidence.length === 1 ? '' : 's'} retrieved.`
    : 'No relevant private source found for this topic.';
  const repairFocus = result?.repair_focus || [];
  const verdictLabel = result?.verdict === 'needs_repair' ? 'Needs repair' : 'Ready for review';
  const medicalGateAvailable = !!(authState.user || appConfig.demoAuthBypass);
  const showRepair = medicalGateAvailable && appConfig.medicalKnowledgeEnabled && result?.verdict === 'needs_repair';
  setStageDetail('quality', result?.verdict === 'needs_repair'
    ? 'Quality gate found weak or missing medical coverage. Repair can use backend-only private references.'
    : (hasRelevantEvidence
      ? 'Quality gate completed. Review citations and save the version you want to keep.'
      : 'Generated anchors were checked, but no relevant private source material was found.'));

  document.getElementById('quality-result').innerHTML = `
    <div class="quality-grid">
      <div class="quality-summary ${result?.verdict === 'needs_repair' ? 'quality-error' : 'quality-success'}">
        <div class="quality-kicker">Medical Quality Gate</div>
        <div class="quality-verdict">${escapeHtml(verdictLabel)}</div>
        <div class="quality-copy">${escapeHtml(coverageLabel)} • ${escapeHtml(evidenceLabel)}</div>
        ${repairFocus.length ? `<div class="quality-repair">Repair focus: ${escapeHtml(repairFocus.join(', '))}</div>` : ''}
        ${showRepair ? `<div class="quality-actions">
          <button class="btn-copy" id="repair-quality-btn" onclick="repairCurrentPalaceWithMedicalEvidence()">Repair with Medical Evidence</button>
        </div>` : ''}
      </div>
      <div class="quality-citations">
        <div class="quality-kicker">Retrieved Citations</div>
        ${evidence.length ? evidence.map(item => {
          const page = item.page_start === item.page_end
            ? `p${item.page_start || '?'}`
            : `p${item.page_start || '?'}-${item.page_end || '?'}`;
          const score = typeof item.similarity === 'number' ? ` • ${(item.similarity * 100).toFixed(0)}% match` : '';
          return `<div class="quality-citation">
            <span>${escapeHtml(item.source_title || item.source_key || 'Medical source')}</span>
            <small>${escapeHtml(page)}${escapeHtml(score)}</small>
          </div>`;
        }).join('') : '<div class="quality-empty">No relevant citations found for this topic. Upload source material to enable evidence-backed review.</div>'}
      </div>
    </div>`;
}

async function repairCurrentPalaceWithMedicalEvidence() {
  if (!currentStoryData) {
    renderQualityGateMessage('Generate a palace script before running repair.', 'error');
    return;
  }
  if (!authState.user && !appConfig.demoAuthBypass) {
    openAuthModal();
    return;
  }
  if (!currentQualityGateData) {
    await runMedicalQualityGate(currentStoryData);
  }

  const btn = document.getElementById('repair-quality-btn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spin"></span> Repairing...';
  }
  setStatus('quality', 'Repairing...', 'running');
  setStageDetail('quality', 'Retrieving private evidence and rewriting weak anchors while preserving the scene.');

  try {
    const token = getMedicalAuthToken();
    const topic = document.getElementById('topic').value.trim();
    const contextPayload = await MnemorizedMedicalApi.context(token, {
      topic,
      max_chunks: 6,
    });
    const evidence = (contextPayload.context || []).map((item, index) => {
      const page = item.page_start === item.page_end
        ? `p${item.page_start || '?'}`
        : `p${item.page_start || '?'}-${item.page_end || '?'}`;
      return `[${index + 1}] ${item.source_title || item.source_key || 'Medical source'} ${page}: ${item.excerpt || ''}`;
    }).join('\n');
    const repairFocus = (currentQualityGateData?.repair_focus || []).join('\n- ');

    const res = await claudeFetch(withAdvisor({
      model: CLAUDE_MODEL,
      max_tokens: 8192,
      system: `You repair medical memory-palace scripts using private reference evidence. Preserve the scene's strongest ideas, but fix missing or weak medical coverage. Use the evidence excerpts only as support; do not quote long source passages. Return ONLY XML tags in the same schema: <scene_title>, <opening>, repeated <vo_line> blocks, and <review_script>. Keep 8-10 anchors unless the topic truly needs fewer. Each <vo_line> must contain HOOK, NARRATION, VISUAL, and ANCHOR fields. HOOK states the encoding strategy (sound-alike, look-alike, functional, contrast, or spatial) and why the visual encodes the fact. Anchors should pass the silhouette test — recognizable by shape alone without reading text. Use visual-mnemonic design principles only; do not copy named scenes, recurring characters, or proprietary symbols from existing commercial mnemonic products.`,
      messages: [{
        role: 'user',
        content: `Clinical topic: ${topic}

Repair focus from the medical quality gate:
- ${repairFocus || 'No specific repair focus returned; improve medical coverage against the retrieved evidence.'}

Private evidence excerpts and citations:
${evidence || 'No evidence excerpts returned.'}

Current script JSON:
${JSON.stringify(currentStoryData, null, 2)}

Repair requirements:
- Preserve the scene title and setting if they still work.
- Keep strong existing anchors when medically sound.
- Rewrite or add anchors for any missing/weak repair-focus concepts.
- Maintain concise visual descriptions and specific board-level medical facts.
- Return XML only.`
      }]
    }));

    if (!res.ok) {
      throw new Error(`Repair provider call failed (HTTP ${res.status}).`);
    }
    const raw = await res.json();
    const repairedText = parseProviderContent(raw, 'Medical Repair');
    const repairedStory = parseStoryXml(repairedText);
    const repairedValidation = validateStoryData(repairedStory);
    if (repairedValidation.fatal.length) {
      throw new Error(`Repair response failed story validation: ${repairedValidation.fatal.join(' ')}`);
    }

    currentQualityGateData = null;
    currentStoryData = repairedStory;
    renderStoryData(repairedStory);
    setStatus('story', '✓ Repaired', 'done');
    await runMedicalQualityGate(repairedStory);

    if (typeof rebuildImagePromptsForStory === 'function') {
      await rebuildImagePromptsForStory(repairedStory);
    } else {
      currentPromptData = { prompt1: '', prompt2: '' };
      setStatus('prompt', 'Rebuild prompts needed', '');
      setStageDetail('prompt', 'The repaired script is ready, but image prompts need a manual rebuild.');
    }
    const warningSuffix = repairedValidation.warnings.length
      ? ` ${repairedValidation.warnings.length} script warning(s) remain for review.`
      : '';
    setLibraryStatus(`Medical repair complete. Review the updated script, then save a new version.${warningSuffix}`, 'success');
  } catch (error) {
    setStatus('quality', 'Repair failed', 'error');
    setStageDetail('quality', 'Repair did not complete. The prior script is still visible for review.');
    renderQualityGateMessage(`Medical repair failed: ${error.message}`, 'error');
  } finally {
    const repairBtn = document.getElementById('repair-quality-btn');
    if (repairBtn) {
      repairBtn.disabled = false;
      repairBtn.textContent = 'Repair with Medical Evidence';
    }
  }
}

async function runMedicalQualityGate(storyData = currentStoryData, clinicalConcepts = null) {
  currentQualityGateData = null;
  if (!storyData) {
    setStatus('quality', 'Waiting...', '');
    setStageDetail('quality', 'Quality gate waits until a palace script exists.');
    renderQualityGateMessage('Generate a palace script before checking medical evidence.');
    return;
  }

  showBody('quality');
  if (!authState.user && !appConfig.demoAuthBypass) {
    setStatus('quality', 'Sign in required', 'error');
    setStageDetail('quality', 'Sign in is required because private medical retrieval runs through the backend account context.');
    renderQualityGateMessage('Sign in to run the private medical quality gate.', 'error');
    return;
  }

  if (!backendState.checked) await refreshBackendStatus();
  if (!appConfig.medicalKnowledgeEnabled || !backendState.medicalKnowledgeConfigured) {
    setStatus('quality', 'Medical KB off', 'error');
    setStageDetail('quality', 'The backend is reachable, but private medical knowledge retrieval is not configured.');
    renderQualityGateMessage('Medical knowledge is not configured on this backend yet.', 'error');
    return;
  }

  setStatus('quality', 'Checking evidence...', 'running');
  setStageDetail('quality', 'Retrieving backend-only reference snippets and checking generated anchors.');
  renderQualityGateMessage('Retrieving private medical citations and checking generated anchors...', 'muted', 'Evidence Check');
  try {
    const result = await MnemorizedMedicalApi.qualityCheck(getMedicalAuthToken(), {
      topic: document.getElementById('topic').value.trim(),
      generation_outputs: { story: storyData },
      required_concepts: (clinicalConcepts && clinicalConcepts.length) ? clinicalConcepts : getQualityGateConcepts(storyData),
      max_evidence_chunks: 6,
    });
    currentQualityGateData = result;
    renderQualityGateResult(result);
    const statusLabel = result.evidence_status === 'no_relevant_source'
      ? 'No source match'
      : (result.verdict === 'needs_repair' ? 'Needs review' : 'Evidence checked');
    setStatus('quality', statusLabel, result.verdict === 'needs_repair' ? 'error' : 'done');
  } catch (error) {
    setStatus('quality', 'Check failed', 'error');
    setStageDetail('quality', 'The script is still available, but the evidence check did not finish.');
    renderQualityGateMessage(`Medical quality check failed: ${error.message}`, 'error');
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
  const qualityGate = outputs.quality_gate || null;
  const prompts = outputs.prompts || {};
  const guidedVideo = outputs.guided_video || null;

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
  setStatus('quality', qualityGate ? 'Evidence loaded' : 'Not checked', qualityGate ? 'done' : '');
  setStatus('prompt', '✓ Loaded', 'done');

  if (story) renderStoryData(story);
  if (qualityGate) {
    currentQualityGateData = qualityGate;
    renderQualityGateResult(qualityGate);
  } else {
    renderQualityGateMessage('This saved palace does not include a medical quality gate result yet.');
  }
  if (prompts.prompt1 || prompts.prompt2) renderPromptData(prompts.prompt1, prompts.prompt2);

  currentPalaceMeta = palaceRow;
  document.getElementById('palace-title-input').value = palaceRow.title || story?.scene_title || '';
  setCurrentPalaceData(story, prompts.prompt1, prompts.prompt2);
  window.MnemorizedGuided?.restoreSnapshot?.(guidedVideo);
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
    document.getElementById('auth-summary').textContent = `Signed in as ${authState.user.email || authState.user.id}. ${appConfig.billingMessage} Save here, then manage the full collection from Library.`;
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
    if (appConfig.demoAuthBypass) {
      setAccountBadge('online', 'DEMO');
      document.getElementById('auth-summary').textContent = 'Demo auth bypass is active for Forge generation. Sign in only when you want to save palaces or use the personal library.';
      setAuthModalStatus('Demo auth bypass is active for provider calls. Library saves still require a real account.');
      openAuthBtn.textContent = 'Demo Auth';
      saveBtn.disabled = true;
      saveBtn.textContent = 'Save Palace';
      saveAsNewBtn.disabled = true;
      newDraftBtn.disabled = true;
      refreshBtn.disabled = true;
      signOutBtn.style.display = 'none';
      renderLibraryRows([]);
      setLibraryStatus('Demo mode: generation works without sign-in; sign in to save to Library.', 'success');
      return;
    }

    setAccountBadge('warning', 'SIGN IN');
    document.getElementById('auth-summary').textContent = `Sign in to save palaces, keep a history, and build your personal library. ${appConfig.billingMessage}`;
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
  const saveBtn = document.getElementById(asNew ? 'save-as-new-btn' : 'save-palace-btn');
  const originalSaveLabel = saveBtn?.textContent || '';
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
  }

  try {
    const result = await MnemorizedPalaceApi.save(getAuthToken(), {
      palace_id: asNew ? null : currentPalaceMeta?.id || null,
      snapshot
    });
    const palaceRow = result.palace;
    const nextVersion = result.version_number || palaceRow.latest_version_number || 1;

    currentPalaceMeta = palaceRow;
    document.getElementById('palace-title-input').value = palaceRow.title || '';
    const savedMessage = `Saved to Library: "${palaceRow.title}" version ${nextVersion}.`;
    setLibraryStatus(savedMessage, 'success');
    refreshAuthUI();
    const primarySaveBtn = document.getElementById('save-palace-btn');
    if (primarySaveBtn && !primarySaveBtn.disabled) {
      primarySaveBtn.textContent = 'Saved';
      setTimeout(refreshAuthUI, 1800);
    }
    await loadLibrary();
    setLibraryStatus(savedMessage, 'success');
  } catch (error) {
    setLibraryStatus(`Save failed: ${error.message}`, 'error');
    if (saveBtn) saveBtn.textContent = originalSaveLabel;
  } finally {
    if (saveBtn) saveBtn.disabled = !hasSavablePalace();
  }
}

// ── Catalog publish ──────────────────────────────────────────────

async function publishToCatalog() {
  if (!authState.user) {
    openAuthModal();
    return;
  }
  if (!hasSavablePalace()) {
    document.getElementById('catalog-publish-status').textContent = 'Generate a palace first.';
    return;
  }

  const tagsRaw = document.getElementById('catalog-tags-input')?.value || '';
  const tags = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);
  const snapshot = buildPalaceSnapshot();
  const statusEl = document.getElementById('catalog-publish-status');
  statusEl.textContent = 'Publishing…';
  statusEl.style.color = 'var(--muted)';

  try {
    const result = await MnemorizedCatalogApi.publish(getAuthToken(), {
      title: snapshot.title,
      topic: snapshot.topic,
      source_name: snapshot.source_name,
      scene_title: snapshot.scene_title,
      tags,
      generation_inputs: snapshot.generation_inputs,
      generation_outputs: snapshot.generation_outputs,
    });
    statusEl.textContent = `Published "${result.entry.title}" to the catalog.`;
    statusEl.style.color = 'var(--green)';
  } catch (error) {
    statusEl.textContent = `Publish failed: ${error.message}`;
    statusEl.style.color = '#fca5a5';
  }
}

// ── Catalog clone ────────────────────────────────────────────────

async function maybeLoadCatalogPalace() {
  if (!catalogIdFromRoute || catalogRouteHydrated) return;
  catalogRouteHydrated = true;

  try {
    const payload = await MnemorizedCatalogApi.get(catalogIdFromRoute);
    const entry = payload.entry;
    if (!entry) throw new Error('Catalog entry not found.');

    const syntheticPalaceRow = {
      id: null,
      title: entry.title,
      topic: entry.topic,
      source_name: entry.source_name,
      scene_title: entry.scene_title,
      status: 'generated',
      latest_version_number: 0,
    };
    const syntheticVersionRow = {
      generation_inputs: entry.generation_inputs,
      generation_outputs: entry.generation_outputs,
    };

    applyPalaceSnapshot(syntheticPalaceRow, syntheticVersionRow);
    currentPalaceMeta = null;
    document.getElementById('palace-title-input').value = entry.title;
    setLibraryStatus(`Loaded "${entry.title}" from the public catalog. Save to add it to your library.`, 'success');
  } catch (error) {
    setLibraryStatus(`Catalog load failed: ${error.message}`, 'error');
  }

  const url = new URL(window.location.href);
  url.searchParams.delete('catalog');
  window.history.replaceState({}, '', url.toString());
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
    appConfig.demoAuthBypass = !!config.demo_auth_bypass_enabled;
    appConfig.medicalKnowledgeEnabled = !!config.medical_knowledge_enabled;
    appConfig.devMode = !!config.dev_mode;
    if (appConfig.devMode) {
      const replaySelect = document.getElementById('replay-select');
      const replayBadge = document.getElementById('replay-badge');
      if (replaySelect) replaySelect.style.display = '';
      if (replayBadge) replayBadge.style.display = '';
    }
    appConfig.billingMode = config.billing_mode || 'beta';
    appConfig.betaMode = !!config.beta_mode;
    appConfig.billingEnabled = !!config.billing_enabled;
    appConfig.upgradeEnabled = !!config.upgrade_enabled;
    appConfig.upgradePathEnabled = !!config.upgrade_path_enabled;
    appConfig.billingMessage = config.billing_message || appConfig.billingMessage;
    appConfig.quotaUnitLabel = config.quota_unit_label || 'AI requests';

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
    await maybeLoadCatalogPalace();
  } catch (error) {
    appConfig.authEnabled = false;
    supabaseClient = null;
    refreshAuthUI();
    setAuthModalStatus(`Auth config load failed: ${error.message}`, 'error');
  }
}

refreshAuthUI();
loadAuthSystem();
