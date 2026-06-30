// ══════════════════════════════════════════════════
// FORGE UPLOAD — Stage 0 document intelligence
// Depends on: forge-state.js, forge-auth.js
// ══════════════════════════════════════════════════

let uploadedFileData = null;
let documentSections = [];
let selectedSectionText = '';

// ── Drag & Drop ───────────────────────────────────────────────────

const zone = document.getElementById('upload-zone');
if (zone) {
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('dragover');
    const f = e.dataTransfer.files[0];
    if (f) processFile(f);
  });
}

async function handleFileSelect(e) {
  const f = e.target.files[0];
  if (f) processFile(f);
}

async function processFile(file) {
  document.getElementById('optional-upload')?.setAttribute('open', '');

  const ext = file.name.split('.').pop().toLowerCase();
  const allowedExts = ['pdf','txt','text','png','jpg','jpeg','webp'];
  const allowedMimeTypes = ['application/pdf','text/plain','image/png','image/jpeg','image/webp'];
  if (!allowedExts.includes(ext) || (file.type && !allowedMimeTypes.includes(file.type))) {
    alert('Unsupported file type. Please upload PDF, TXT, PNG, or JPG.');
    return;
  }

  const isImage = ['png','jpg','jpeg','webp'].includes(ext);
  const isText  = ['txt','text'].includes(ext);

  document.getElementById('file-status').style.display = 'flex';
  document.getElementById('file-status-name').textContent = file.name;
  document.getElementById('file-status-size').textContent = `(${(file.size/1024).toFixed(0)} KB)`;
  document.getElementById('file-status-icon').textContent = isImage ? '🖼' : ext === 'pdf' ? '📄' : '📝';

  const reader = new FileReader();

  if (isText) {
    reader.onload = e => {
      uploadedFileData = { name: file.name, type: ext, base64: null, text: e.target.result, isImage: false };
      document.getElementById('extract-btn-wrap').style.display = 'block';
    };
    reader.readAsText(file);
  } else {
    reader.onload = e => {
      const b64 = e.target.result.split(',')[1];
      uploadedFileData = { name: file.name, type: ext, base64: b64, text: null, isImage };
      document.getElementById('extract-btn-wrap').style.display = 'block';
    };
    reader.readAsDataURL(file);
  }
}

function clearFile() {
  uploadedFileData = null; documentSections = []; selectedSectionText = '';
  document.getElementById('file-input').value = '';
  document.getElementById('file-status').style.display = 'none';
  document.getElementById('extract-btn-wrap').style.display = 'none';
  document.getElementById('section-picker-wrap').style.display = 'none';
  document.getElementById('concepts-btn-wrap').style.display = 'none';
  document.getElementById('checklist-wrap').style.display = 'none';
}

// ── Section Extraction ────────────────────────────────────────────

async function extractSections() {
  const btn = document.getElementById('extract-btn');
  const btnText = document.getElementById('extract-btn-text');
  btn.disabled = true;
  btnText.textContent = '✦ Identifying sections…';

  const messages = buildFileMessage(
    `You are a medical educator analyzing a document. Identify all distinct sections, topics, or chapters in this document.

Respond ONLY with XML. No preamble, no explanation.

<sections>
<section><title>Section name (concise, 2-6 words)</title><summary>One sentence describing what this section covers and what it would be good to memorize.</summary></section>
</sections>

List every distinct section. If the document is one continuous topic with no clear sections, create logical sub-topic groupings of 4–8 concepts each.`
  );

  try {
    const res = await claudeFetch({ model: CLAUDE_MODEL, max_tokens: 1200, messages });
    const data = await res.json();
    if (data.error) throw new Error(data.error.message || 'API error');
    const txt = data.content?.[0]?.text || '';

    const titleMatches = [...txt.matchAll(/<title>([\s\S]*?)<\/title>/gi)].map(m => m[1].trim());
    const summaryMatches = [...txt.matchAll(/<summary>([\s\S]*?)<\/summary>/gi)].map(m => m[1].trim());

    documentSections = titleMatches.map((t, i) => ({ title: t, summary: summaryMatches[i] || '' }));

    if (!documentSections.length) throw new Error('No sections found. Try a different file.');

    const sel = document.getElementById('section-select');
    sel.innerHTML = '<option value="">— choose a section —</option>';
    documentSections.forEach((s, i) => {
      const opt = document.createElement('option');
      opt.value = i;
      opt.textContent = s.title;
      opt.title = s.summary;
      sel.appendChild(opt);
    });

    document.getElementById('section-picker-wrap').style.display = 'block';
    btnText.textContent = `✓ Found ${documentSections.length} sections`;
  } catch(e) {
    btnText.textContent = '✗ ' + e.message;
    btn.disabled = false;
  }
}

function onSectionChange() {
  const val = document.getElementById('section-select').value;
  document.getElementById('concepts-btn-wrap').style.display = val !== '' ? 'block' : 'none';
  document.getElementById('checklist-wrap').style.display = 'none';
}

// ── Concept Extraction ────────────────────────────────────────────

async function extractConcepts() {
  const idx = parseInt(document.getElementById('section-select').value);
  const section = documentSections[idx];
  const btn = document.getElementById('concepts-btn');
  const btnText = document.getElementById('concepts-btn-text');
  btn.disabled = true;
  btnText.textContent = '✦ Extracting high-yield concepts…';

  const messages = buildFileMessage(
    `You are a senior medical educator and board exam question writer. Extract EVERY high-yield, board-testable concept from the section titled "${section.title}" in this document.

High-yield means: commonly tested, clinically important, or frequently pimped on rounds. Include:
- Mechanisms, pathophysiology
- Drug names, classes, receptor affinities, indications, contraindications
- Key numbers, thresholds, doses
- Classic presentations, buzzword findings
- Management algorithms and decision points
- Diagnostic criteria
- Common clinical mistakes / pitfalls

Respond ONLY with XML. No preamble.

<concepts>
<concept>
<text>The specific fact, mechanism, or clinical pearl — written as a crisp, self-contained learning point</text>
<category>one of: Mechanism | Drug | Numbers | Presentation | Management | Diagnosis | Pitfall</category>
</concept>
</concepts>

Extract every testable concept. Do not summarize or collapse related items — list each separately.`
  );

  try {
    const res = await claudeFetch({ model: CLAUDE_MODEL, max_tokens: 2500, messages });
    const data = await res.json();
    if (data.error) throw new Error(data.error.message || 'API error');
    const txt = data.content?.[0]?.text || '';

    const textMatches = [...txt.matchAll(/<text>([\s\S]*?)<\/text>/gi)].map(m => m[1].trim());
    const catMatches  = [...txt.matchAll(/<category>([\s\S]*?)<\/category>/gi)].map(m => m[1].trim());

    if (!textMatches.length) throw new Error('No concepts extracted. Try a different section.');

    const container = document.getElementById('concept-checklist');
    container.innerHTML = '';
    textMatches.forEach((text, i) => {
      const cat = catMatches[i] || '';
      const item = document.createElement('div');
      item.className = 'concept-item';
      item.dataset.idx = i;
      item.setAttribute('role', 'checkbox');
      item.setAttribute('aria-checked', 'true');
      item.setAttribute('tabindex', '0');
      item.innerHTML = `
        <div class="concept-check"></div>
        <div class="flex-col" style="flex:1">
          <div class="concept-text">${escapeHtml(text)}</div>
          ${cat ? `<div class="concept-tag">${escapeHtml(cat)}</div>` : ''}
        </div>`;
      function toggleItem() {
        item.classList.toggle('excluded');
        item.setAttribute('aria-checked', item.classList.contains('excluded') ? 'false' : 'true');
        updateChecklistCount();
      }
      item.addEventListener('click', toggleItem);
      item.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleItem(); }
      });
      container.appendChild(item);
    });

    updateChecklistCount();
    document.getElementById('checklist-wrap').style.display = 'block';
    btnText.textContent = `✓ Extracted ${textMatches.length} concepts`;
  } catch(e) {
    btnText.textContent = '✗ ' + e.message;
    btn.disabled = false;
  }
}

function updateChecklistCount() {
  const total = document.querySelectorAll('.concept-item').length;
  const selected = document.querySelectorAll('.concept-item:not(.excluded)').length;
  document.getElementById('checklist-count').textContent = `${selected} of ${total} selected`;
}

function toggleAll(on) {
  document.querySelectorAll('.concept-item').forEach(el => {
    if (on) el.classList.remove('excluded');
    else el.classList.add('excluded');
    el.setAttribute('aria-checked', on ? 'true' : 'false');
  });
  updateChecklistCount();
}

function proceedToForge() {
  const selected = [...document.querySelectorAll('.concept-item:not(.excluded)')]
    .map(el => el.querySelector('.concept-text').textContent.trim());

  if (!selected.length) { alert('Select at least one concept.'); return; }

  const sectionTitle = documentSections[parseInt(document.getElementById('section-select').value)]?.title || '';
  const topicText = (sectionTitle ? `[${sectionTitle}]\n` : '') + selected.join('\n');
  document.getElementById('topic').value = topicText;

  document.getElementById('config-wrap').style.display = 'block';
  document.getElementById('forge-wrap').style.display = 'block';

  setTimeout(() => document.getElementById('topic').scrollIntoView({ behavior: 'smooth', block: 'center' }), 100);
}

function skipUpload() {
  document.getElementById('config-wrap').style.display = 'block';
  document.getElementById('forge-wrap').style.display = 'block';
  setTimeout(() => document.getElementById('config-wrap').scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
}

// ── Build API message with correct content type ───────────────────

function buildFileMessage(prompt) {
  if (!uploadedFileData) return [{ role: 'user', content: prompt }];

  const { type, base64, text, isImage } = uploadedFileData;

  if (text) {
    return [{ role: 'user', content: `${prompt}\n\n<document>\n${text.slice(0, 60000)}\n</document>` }];
  }

  if (isImage) {
    const mediaMap = { png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', webp: 'image/webp' };
    return [{
      role: 'user',
      content: [
        { type: 'image', source: { type: 'base64', media_type: mediaMap[type] || 'image/png', data: base64 } },
        { type: 'text', text: prompt }
      ]
    }];
  }

  if (type === 'pdf') {
    return [{
      role: 'user',
      content: [
        { type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: base64 } },
        { type: 'text', text: prompt }
      ]
    }];
  }

  return [{ role: 'user', content: prompt }];
}
