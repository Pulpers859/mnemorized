// Guided lesson builder: anchor coordinates, ElevenLabs handoff, and pan/highlight preview.
(function() {
  const DEFAULT_COORDS = [
    [0.16, 0.22], [0.34, 0.24], [0.52, 0.24], [0.70, 0.24], [0.86, 0.24],
    [0.18, 0.55], [0.36, 0.58], [0.54, 0.58], [0.72, 0.58], [0.86, 0.60],
    [0.24, 0.80], [0.48, 0.82], [0.72, 0.82]
  ];
  const WORDS_PER_SECOND = 2.45;

  const state = {
    story: null,
    segments: [],
    coords: [],
    selectedAnchor: 1,
    audioName: '',
    audioDuration: 0,
    audioStoragePath: '',
    audioStorage: '',
    audioBlob: null,
    _currentAudioUrl: null,
    useAudioTiming: false,
    previewTimer: null,
    previewStartedAt: 0,
    previewRunning: false
  };

  let _restoreGeneration = 0;

  function $(id) {
    return document.getElementById(id);
  }

  function _revokeAudioUrl() {
    if (state._currentAudioUrl) {
      URL.revokeObjectURL(state._currentAudioUrl);
      state._currentAudioUrl = null;
    }
  }

  function escapeLocalHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function clamp01(value) {
    const n = Number(value);
    if (Number.isNaN(n)) return 0.5;
    return Math.max(0, Math.min(1, n));
  }

  function getStory() {
    if (state.story?.voLines?.length) return state.story;
    if (typeof currentStoryData !== 'undefined' && currentStoryData?.voLines?.length) {
      return currentStoryData;
    }
    return null;
  }

  function getFinalImageSrc() {
    const result = $('gen-img-result-el')?.src;
    if (result && !result.endsWith('/') && !result.startsWith(window.location.href)) return result;
    const second = $('gen-img-2-el')?.src;
    if (second && !second.endsWith('/') && !second.startsWith(window.location.href)) return second;
    const first = $('gen-img-1-el')?.src;
    if (first && !first.endsWith('/') && !first.startsWith(window.location.href)) return first;
    return '';
  }

  function estimateSeconds(text) {
    const words = String(text || '').trim().split(/\s+/).filter(Boolean).length;
    return Math.max(5, Math.min(22, Math.round(words / WORDS_PER_SECOND)));
  }

  function defaultCoordFor(index) {
    const pair = DEFAULT_COORDS[index % DEFAULT_COORDS.length];
    return { x: pair[0], y: pair[1] };
  }

  function normalizeCoord(coord, index, line) {
    const fallback = defaultCoordFor(index);
    return {
      n: Number(coord?.n || line?.n || index + 1),
      x: clamp01(coord?.x ?? fallback.x),
      y: clamp01(coord?.y ?? fallback.y),
      found: coord?.found !== false,
      note: coord?.note || '',
      encodes: line?.anchor || coord?.encodes || '',
      visual: line?.visual || coord?.visual || ''
    };
  }

  function makeSegments(story, existingSegments = []) {
    let cursor = 0;
    return (story.voLines || []).map((line, index) => {
      const prior = existingSegments.find(item => Number(item.n) === Number(line.n));
      const duration = Number(prior?.duration_seconds) || estimateSeconds(line.narration);
      const segment = {
        n: Number(line.n || index + 1),
        start_seconds: Number(prior?.start_seconds ?? cursor),
        duration_seconds: duration,
        end_seconds: Number(prior?.end_seconds ?? cursor + duration),
        narration: line.narration || '',
        visual: line.visual || '',
        anchor: line.anchor || '',
        hook: line.hook || ''
      };
      cursor = segment.end_seconds;
      return segment;
    });
  }

  function buildElevenLabsScript(story) {
    if (!story) return '';
    const lines = [];
    if (story.scene_title) lines.push(story.scene_title);
    if (story.opening) {
      lines.push('');
      lines.push(story.opening);
    }
    (story.voLines || []).forEach(line => {
      lines.push('');
      lines.push(`Anchor ${line.n}`);
      lines.push(String(line.narration || '').trim());
    });
    if (story.review_script) {
      lines.push('');
      lines.push('Rapid review');
      lines.push(String(story.review_script || '').trim());
    }
    return lines.join('\n');
  }

  function setStatus(message, tone = 'muted') {
    const el = $('guided-status');
    if (!el) return;
    el.textContent = message;
    el.style.color = tone === 'success' ? 'var(--green)' : tone === 'error' ? '#fca5a5' : 'var(--muted)';
  }

  function setPreviewImage(src) {
    const img = $('guided-preview-image');
    if (!img) return false;
    if (!src) {
      setStatus('Generate or load a palace image before previewing the guided lesson.', 'error');
      return false;
    }
    img.src = src;
    return true;
  }

  function activeSegmentAt(seconds) {
    if (!state.segments.length) return null;
    const estimatedTotal = totalDuration();
    const mappedSeconds = state.useAudioTiming && state.audioDuration > 0 && estimatedTotal > 0
      ? seconds * (estimatedTotal / state.audioDuration)
      : seconds;
    return state.segments.find(item => mappedSeconds >= item.start_seconds && mappedSeconds < item.end_seconds)
      || state.segments[state.segments.length - 1];
  }

  function updateActiveAnchor(n) {
    state.selectedAnchor = Number(n) || 1;
    renderPins();
    renderAnchorRows();
    focusAnchor(state.selectedAnchor);
  }

  function getCoord(n) {
    return state.coords.find(item => Number(item.n) === Number(n));
  }

  function focusAnchor(n) {
    const coord = getCoord(n);
    const img = $('guided-preview-image');
    const highlight = $('guided-highlight');
    if (!coord || !img || !highlight) return;
    img.style.transformOrigin = `${coord.x * 100}% ${coord.y * 100}%`;
    img.style.transform = 'scale(1.18)';
    img.style.filter = 'saturate(1.05) contrast(1.03)';
    highlight.style.left = `${coord.x * 100}%`;
    highlight.style.top = `${coord.y * 100}%`;
    highlight.style.opacity = '1';
  }

  function clearFocus() {
    const img = $('guided-preview-image');
    const highlight = $('guided-highlight');
    if (img) {
      img.style.transform = 'scale(1)';
      img.style.filter = '';
    }
    if (highlight) highlight.style.opacity = '0';
  }

  function renderPins() {
    const layer = $('guided-pin-layer');
    if (!layer) return;
    layer.innerHTML = state.coords.map(coord => `
      <button class="guided-pin" type="button" style="left:${coord.x * 100}%;top:${coord.y * 100}%;" onclick="guidedSelectAnchor(${coord.n});event.stopPropagation();" title="Anchor ${coord.n}">
        ${coord.n}
      </button>
    `).join('');
  }

  function renderAnchorRows() {
    const list = $('guided-anchor-list');
    if (!list) return;
    if (!state.segments.length) {
      list.innerHTML = '<div class="guided-copy" style="padding:12px 0;">Build a guided plan after the script is ready.</div>';
      return;
    }
    list.innerHTML = state.segments.map(segment => {
      const coord = getCoord(segment.n) || defaultCoordFor(segment.n - 1);
      const label = segment.anchor || segment.visual || `Anchor ${segment.n}`;
      const active = Number(segment.n) === Number(state.selectedAnchor) ? ' active' : '';
      return `
        <div class="guided-anchor-row${active}" onclick="guidedSelectAnchor(${segment.n})">
          <span class="row-num">${segment.n}</span>
          <span class="guided-anchor-name" title="${escapeLocalHtml(label)}">${escapeLocalHtml(label)}</span>
          <input aria-label="Anchor ${segment.n} x coordinate" type="number" min="0" max="1" step="0.01" value="${coord.x.toFixed(2)}" onchange="guidedSetCoord(${segment.n}, 'x', this.value)" onclick="event.stopPropagation();">
          <input aria-label="Anchor ${segment.n} y coordinate" type="number" min="0" max="1" step="0.01" value="${coord.y.toFixed(2)}" onchange="guidedSetCoord(${segment.n}, 'y', this.value)" onclick="event.stopPropagation();">
        </div>
      `;
    }).join('');
  }

  function renderAll() {
    const story = getStory();
    const textarea = $('guided-elevenlabs-script');
    if (textarea) textarea.value = buildElevenLabsScript(story);
    renderPins();
    renderAnchorRows();
    const src = getFinalImageSrc();
    if (src) setPreviewImage(src);
  }

  function buildPlan(options = {}) {
    const story = options.story || getStory();
    if (!story?.voLines?.length) {
      setStatus('Forge a palace script before building a guided lesson.', 'error');
      return false;
    }
    const existingCoords = options.coords || state.coords;
    state.story = story;
    state.segments = makeSegments(story, options.segments || state.segments);
    state.coords = story.voLines.map((line, index) => {
      const prior = existingCoords.find(item => Number(item.n) === Number(line.n));
      return normalizeCoord(prior, index, line);
    });
    state.selectedAnchor = state.segments[0]?.n || 1;
    renderAll();
    setStatus(`Guided plan ready: ${state.segments.length} anchors, ${Math.round(totalDuration())} sec estimated. Export the script to ElevenLabs Studio, then upload the audio here.`, 'success');
    return true;
  }

  function totalDuration() {
    if (!state.segments.length) return 0;
    return Math.max(...state.segments.map(item => Number(item.end_seconds) || 0));
  }

  function stopPreview() {
    state.previewRunning = false;
    if (state.previewTimer) {
      cancelAnimationFrame(state.previewTimer);
      state.previewTimer = null;
    }
    const audio = $('guided-audio');
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    clearFocus();
  }

  function previewTick() {
    if (!state.previewRunning) return;
    const audio = $('guided-audio');
    const seconds = audio && audio.src ? audio.currentTime : (performance.now() - state.previewStartedAt) / 1000;
    const segment = activeSegmentAt(seconds);
    if (segment) updateActiveAnchor(segment.n);
    if ((!audio?.src && seconds >= totalDuration()) || (audio?.src && audio.ended)) {
      stopPreview();
      return;
    }
    state.previewTimer = requestAnimationFrame(previewTick);
  }

  function playPreview() {
    if (!state.segments.length && !buildPlan()) return;
    if (!setPreviewImage(getFinalImageSrc() || $('guided-preview-image')?.src || '')) return;
    stopPreview();
    state.previewRunning = true;
    state.previewStartedAt = performance.now();
    const audio = $('guided-audio');
    if (audio?.src) {
      audio.currentTime = 0;
      state.useAudioTiming = true;
      audio.play().catch(error => {
        state.useAudioTiming = false;
        state.previewStartedAt = performance.now();
        setStatus(`Audio playback blocked: ${error.message}. Playing estimated-timing preview instead.`, 'error');
      });
    } else {
      state.useAudioTiming = false;
    }
    setStatus(audio?.src ? 'Playing guided preview with uploaded audio.' : 'Playing estimated-timing preview. Upload ElevenLabs audio for real timing.', 'success');
    previewTick();
  }

  function copyScript() {
    const text = $('guided-elevenlabs-script')?.value || '';
    if (!text.trim() && !buildPlan()) return;
    navigator.clipboard.writeText($('guided-elevenlabs-script')?.value || '')
      .then(() => setStatus('Narration script copied for ElevenLabs Studio.', 'success'))
      .catch(error => setStatus(`Copy failed: ${error.message}`, 'error'));
  }

  function downloadText(filename, text, type = 'text/plain') {
    const blob = new Blob([text], { type });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function safeTopicName() {
    const topic = $('topic')?.value?.trim() || state.story?.scene_title || 'guided_lesson';
    return topic.replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_+|_+$/g, '').substring(0, 48) || 'guided_lesson';
  }

  function getSnapshot() {
    return {
      version: 1,
      provider_workflow: 'manual-elevenlabs-studio',
      anchor_coords: state.coords,
      narration_segments: state.segments,
      audio: state.audioName ? {
        name: state.audioName,
        duration_seconds: state.audioDuration || null,
        storage: state.audioStorage || 'local-browser-upload-only',
        storage_path: state.audioStoragePath || null
      } : null
    };
  }

  function restoreSnapshot(snapshot) {
    if (!snapshot) {
      reset();
      return;
    }
    const story = getStory();
    state.coords = Array.isArray(snapshot.anchor_coords) ? snapshot.anchor_coords : [];
    state.segments = Array.isArray(snapshot.narration_segments) ? snapshot.narration_segments : [];
    state.audioName = snapshot.audio?.name || '';
    state.audioDuration = Number(snapshot.audio?.duration_seconds) || 0;
    state.audioStorage = snapshot.audio?.storage || '';
    state.audioStoragePath = snapshot.audio?.storage_path || '';
    if (story?.voLines?.length) {
      buildPlan({ story, coords: state.coords, segments: state.segments });
    } else {
      renderAll();
    }

    if (state.audioStorage === 'supabase' && state.audioName) {
      const palaceId = _currentPalaceId();
      if (palaceId) {
        const thisGen = ++_restoreGeneration;
        setStatus('Loading audio from cloud storage…', 'muted');
        loadAudioFromStorage(palaceId, state.audioName).then(loaded => {
          if (thisGen !== _restoreGeneration) return;
          if (loaded) {
            setStatus(`Audio restored from cloud: ${state.audioName} (${Math.round(state.audioDuration)} sec).`, 'success');
          } else {
            setStatus(`Guided metadata loaded. Audio "${state.audioName}" not found in storage — re-upload or regenerate.`, 'success');
          }
        }).catch(() => {
          if (thisGen !== _restoreGeneration) return;
          setStatus(`Guided metadata loaded. Could not load audio from storage — re-upload or regenerate.`, 'success');
        });
      } else if (state.audioName) {
        setStatus(`Guided metadata loaded. Save palace first, then re-upload "${state.audioName}" to preview.`, 'success');
      }
    } else if (state.audioName) {
      setStatus(`Guided metadata loaded. Re-upload "${state.audioName}" to preview with audio.`, 'success');
    }
  }

  function reset() {
    stopPreview();
    state.story = null;
    state.segments = [];
    state.coords = [];
    state.selectedAnchor = 1;
    state.audioName = '';
    state.audioDuration = 0;
    state.audioStoragePath = '';
    state.audioStorage = '';
    state.audioBlob = null;
    _revokeAudioUrl();
    state.useAudioTiming = false;
    ++_restoreGeneration;
    const textarea = $('guided-elevenlabs-script');
    if (textarea) textarea.value = '';
    const audio = $('guided-audio');
    if (audio) {
      audio.removeAttribute('src');
      audio.style.display = 'none';
    }
    const image = $('guided-preview-image');
    if (image) image.removeAttribute('src');
    renderPins();
    renderAnchorRows();
    clearFocus();
    setStatus('Waiting for a palace script.');
  }

  function importCoords(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result);
        const coords = Array.isArray(parsed) ? parsed : parsed.anchor_coords;
        if (!Array.isArray(coords)) throw new Error('No anchor coordinate array found.');
        state.coords = coords.map((coord, index) => normalizeCoord(coord, index, getStory()?.voLines?.[index]));
        if (getStory()) buildPlan({ story: getStory(), coords: state.coords, segments: state.segments });
        renderAll();
        setStatus(`Imported ${state.coords.length} anchor coordinates.`, 'success');
      } catch (error) {
        setStatus(`Coordinate import failed: ${error.message}`, 'error');
      }
    };
    reader.readAsText(file);
  }

  function wireEvents() {
    const layer = $('guided-pin-layer');
    if (layer) {
      layer.addEventListener('click', event => {
        if (!state.segments.length && !buildPlan()) return;
        const rect = layer.getBoundingClientRect();
        const coord = getCoord(state.selectedAnchor);
        if (!coord) return;
        coord.x = clamp01((event.clientX - rect.left) / rect.width);
        coord.y = clamp01((event.clientY - rect.top) / rect.height);
        renderAll();
        focusAnchor(state.selectedAnchor);
      });
    }

    const audioInput = $('guided-audio-input');
    if (audioInput) {
      audioInput.addEventListener('change', event => {
        const file = event.target.files?.[0];
        if (!file) return;
        const audio = $('guided-audio');
        if (!audio) return;
        _revokeAudioUrl();
        const fileUrl = URL.createObjectURL(file);
        state._currentAudioUrl = fileUrl;
        audio.src = fileUrl;
        audio.style.display = 'block';
        state.audioName = file.name;
        state.audioBlob = file;
        state.audioStorage = '';
        state.audioStoragePath = '';
        audio.onloadedmetadata = () => {
          state.audioDuration = audio.duration || 0;
          setStatus(`Audio loaded: ${file.name} (${Math.round(state.audioDuration)} sec).`, 'success');

          const palaceId = _currentPalaceId();
          if (palaceId) {
            uploadAudioToStorage(file, palaceId, file.name).then(result => {
              if (result) setStatus(`Audio loaded and saved to cloud storage: ${file.name}`, 'success');
            }).catch(() => {});
          }
        };
      });
    }

    const coordsInput = $('guided-coords-input');
    if (coordsInput) {
      coordsInput.addEventListener('change', event => importCoords(event.target.files?.[0]));
    }
  }

  function _authHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (typeof authState !== 'undefined' && authState.session?.access_token) {
      headers.Authorization = `Bearer ${authState.session.access_token}`;
    }
    return headers;
  }

  function _apiUrl(path) {
    return typeof MnemorizedUtils !== 'undefined' ? MnemorizedUtils.getApiUrl(path) : path;
  }

  function _currentPalaceId() {
    return typeof currentPalaceMeta !== 'undefined' && currentPalaceMeta?.id ? currentPalaceMeta.id : null;
  }

  async function uploadAudioToStorage(blob, palaceId, filename) {
    if (!palaceId) return null;
    if (!blob || blob.size === 0) return null;

    const reader = new FileReader();
    const base64 = await new Promise((resolve, reject) => {
      reader.onload = () => {
        const dataUrl = reader.result;
        const comma = dataUrl.indexOf(',');
        resolve(comma >= 0 ? dataUrl.substring(comma + 1) : dataUrl);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });

    const headers = _authHeaders();
    let res = await fetch(_apiUrl('/api/audio/upload'), {
      method: 'POST',
      headers,
      body: JSON.stringify({
        palace_id: palaceId,
        audio_base64: base64,
        content_type: blob.type || 'audio/mpeg',
        filename: filename || 'narration.mp3',
      }),
    });

    if (res.status === 401 && typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
      const { data } = await supabaseClient.auth.refreshSession();
      if (data?.session?.access_token) {
        authState.session = data.session;
        headers.Authorization = `Bearer ${data.session.access_token}`;
        res = await fetch(_apiUrl('/api/audio/upload'), {
          method: 'POST',
          headers,
          body: JSON.stringify({
            palace_id: palaceId,
            audio_base64: base64,
            content_type: blob.type || 'audio/mpeg',
            filename: filename || 'narration.mp3',
          }),
        });
      }
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      console.warn('[Mnemorized] Audio upload to storage failed:', err);
      return null;
    }

    const result = await res.json();
    state.audioStoragePath = result.storage_path || '';
    state.audioStorage = 'supabase';
    return result;
  }

  async function loadAudioFromStorage(palaceId, filename) {
    if (!palaceId || !filename) return false;

    const headers = _authHeaders();
    const url = _apiUrl(`/api/audio/${encodeURIComponent(palaceId)}/${encodeURIComponent(filename)}`);
    let res = await fetch(url, { method: 'GET', headers });

    if (res.status === 401 && typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
      const { data } = await supabaseClient.auth.refreshSession();
      if (data?.session?.access_token) {
        authState.session = data.session;
        headers.Authorization = `Bearer ${data.session.access_token}`;
        res = await fetch(url, { method: 'GET', headers });
      }
    }

    if (res.status === 404) return false;
    if (!res.ok) {
      console.warn('[Mnemorized] Audio download from storage failed:', res.status);
      return false;
    }

    const data = await res.json();
    const audioBytes = Uint8Array.from(atob(data.audio_base64), c => c.charCodeAt(0));
    const blob = new Blob([audioBytes], { type: data.content_type || 'audio/mpeg' });
    state.audioBlob = blob;

    _revokeAudioUrl();
    const audioEl = $('guided-audio');
    if (audioEl) {
      const blobUrl = URL.createObjectURL(blob);
      state._currentAudioUrl = blobUrl;
      audioEl.src = blobUrl;
      audioEl.style.display = 'block';
      audioEl.onloadedmetadata = () => {
        state.audioDuration = audioEl.duration || 0;
      };
    }
    return true;
  }

  async function generateAudio() {
    const script = $('guided-elevenlabs-script')?.value || '';
    if (!script.trim() && !buildPlan()) return;
    const text = $('guided-elevenlabs-script')?.value || '';
    if (!text.trim()) {
      setStatus('No narration script to generate audio from.', 'error');
      return;
    }

    const btn = $('guided-generate-audio-btn');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Generating…';
    }
    setStatus('Sending narration to ElevenLabs…', 'muted');

    const headers = _authHeaders();
    const ttsUrl = _apiUrl('/api/elevenlabs/tts');

    try {
      let res = await fetch(ttsUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({ text, voice: '', model_id: 'eleven_multilingual_v2' }),
      });

      if (res.status === 401 && typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
        const { data } = await supabaseClient.auth.refreshSession();
        if (data?.session?.access_token) {
          authState.session = data.session;
          headers.Authorization = `Bearer ${data.session.access_token}`;
          res = await fetch(ttsUrl, {
            method: 'POST',
            headers,
            body: JSON.stringify({ text, voice: '', model_id: 'eleven_multilingual_v2' }),
          });
        }
      }

      if (res.status === 401) {
        if (typeof openAuthModal === 'function') openAuthModal();
        throw new Error('Sign in to generate audio.');
      }
      if (res.status === 402) {
        const quota = await res.json().catch(() => ({}));
        const msg = typeof getQuotaExceededMessage === 'function'
          ? getQuotaExceededMessage(quota) : 'Monthly usage limit reached.';
        throw new Error(msg);
      }
      if (res.status === 503) throw new Error('ElevenLabs API key is not configured on the backend.');
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.error?.message || `ElevenLabs returned status ${res.status}`);
      }

      const data = await res.json();
      const audioBytes = Uint8Array.from(atob(data.audio_base64), c => c.charCodeAt(0));
      const blob = new Blob([audioBytes], { type: data.content_type || 'audio/mpeg' });
      state.audioBlob = blob;
      state.audioStorage = '';
      state.audioStoragePath = '';
      _revokeAudioUrl();
      const audioUrl = URL.createObjectURL(blob);
      state._currentAudioUrl = audioUrl;

      const audio = $('guided-audio');
      const fname = `${safeTopicName()}_elevenlabs.mp3`;
      state.audioName = fname;
      if (audio) {
        audio.src = audioUrl;
        audio.style.display = 'block';
        audio.onloadedmetadata = () => {
          state.audioDuration = audio.duration || 0;
          setStatus(`Audio generated: ${Math.round(state.audioDuration)} sec, ${Math.round(data.size_bytes / 1024)} KB. Ready to preview.`, 'success');
        };
      }

      const palaceId = _currentPalaceId();
      if (palaceId) {
        uploadAudioToStorage(blob, palaceId, fname).catch(() => {
          setStatus(`Audio generated but cloud upload failed. Audio is in browser memory only — save will retry.`, 'success');
        });
      }
    } catch (err) {
      setStatus(`Audio generation failed: ${err.message}`, 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Generate Audio';
      }
    }
  }

  window.guidedGenerateAudio = generateAudio;
  window.guidedBuildPlan = () => buildPlan();
  window.guidedCopyElevenLabsScript = copyScript;
  window.guidedDownloadElevenLabsScript = () => {
    if (!($('guided-elevenlabs-script')?.value || '').trim() && !buildPlan()) return;
    downloadText(`${safeTopicName()}_elevenlabs_script.txt`, $('guided-elevenlabs-script')?.value || '');
    setStatus('Narration script downloaded.', 'success');
  };
  window.guidedExportJson = () => {
    if (!state.segments.length && !buildPlan()) return;
    downloadText(`${safeTopicName()}_guided_lesson.json`, JSON.stringify(getSnapshot(), null, 2), 'application/json');
    setStatus('Guided lesson JSON exported.', 'success');
  };
  window.guidedImportCoordsClick = () => $('guided-coords-input')?.click();
  window.guidedPlayPreview = playPreview;
  window.guidedStopPreview = stopPreview;
  window.guidedUseFinalImage = () => {
    if (setPreviewImage(getFinalImageSrc())) setStatus('Final palace image loaded into guided preview.', 'success');
  };
  window.guidedSelectAnchor = updateActiveAnchor;
  window.guidedSetCoord = (n, axis, value) => {
    const coord = getCoord(n);
    if (!coord || !['x', 'y'].includes(axis)) return;
    coord[axis] = clamp01(value);
    renderAll();
    focusAnchor(n);
  };

  window.MnemorizedGuided = {
    reset,
    onStoryReady: story => buildPlan({ story }),
    onImageReady: src => setPreviewImage(src || getFinalImageSrc()),
    getSnapshot,
    restoreSnapshot,
    getBundleData: getSnapshot
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireEvents);
  } else {
    wireEvents();
  }
  renderAnchorRows();
})();
