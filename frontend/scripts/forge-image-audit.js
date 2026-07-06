// ══════════════════════════════════════════════════
// FORGE IMAGE AUDIT — in-app final-image quality gate
// Loaded after forge-pipeline.js (needs claudeFetch, currentStoryData, escapeHtml).
//
// Until now the >=96 "A+" image audit lived only in docs and offline tools
// (visual_qa_pack.py / stress_visual_pipeline.py) — the running app never scored
// a generated image. This module brings a lightweight version in-app: it sends
// the generated palace image + the anchor list to a vision model, scores anchor
// coverage and the constitution's known failure modes, and enforces the >=96
// PASS bar so the user gets an automated verdict instead of eyeballing it.
// User-triggered (one provider request per run) to respect the cost protocol.
// ══════════════════════════════════════════════════

(function () {
  const TARGET_SCORE = 96;

  // Compact rubric distilled from docs/gemini-constitution.txt confirmed failure
  // modes. Kept in sync conceptually with the offline audit tools.
  const FAILURE_MODES = [
    'Missing or unrecognizable anchors (an anchor from the list is absent or unreadable at 1024px)',
    'Meta-instruction / caption leakage (words like "Hook", "Encodes", "zone", zone names rendered as text)',
    'Wordy labels or too many text surfaces (ordinary label over 3 words, or a label-list crammed on one object)',
    'Misspelled or invented labels (a required exact label rendered with wrong spelling)',
    'Segmented-grid overfitting (scene split into booths/bays/panels instead of one coherent room)',
    'Illegible clutter (anchors shrunk into indistinct shelf clutter with no clear silhouette)',
    'Compound/contradictory spatial placement or duplicated identical silhouettes',
  ];

  function finalImageSrc() {
    const ids = ['gen-img-result-el', 'gen-img-2-el', 'gen-img-1-el'];
    for (const id of ids) {
      const src = document.getElementById(id)?.src || '';
      if (src.startsWith('data:image')) return src;
    }
    return '';
  }

  function auditResultEl() {
    return document.getElementById('image-audit-result');
  }

  function setAuditMessage(html) {
    const el = auditResultEl();
    if (el) el.innerHTML = html;
  }

  function buildAuditPrompt(anchors) {
    const anchorLines = anchors
      .map(a => `${a.n}. ${a.visual || a.anchor || '(anchor)'}${a.anchor ? ` — encodes: ${a.anchor}` : ''}`)
      .join('\n');
    return `You are an exacting visual-mnemonic image auditor. Score the attached memory-palace illustration against the anchor list and the known failure modes. Never inflate the score; a genuinely publishable board-study plate scores >=${TARGET_SCORE}.

ANCHORS THAT SHOULD APPEAR (each must be a recognizable visual, readable at normal size):
${anchorLines}

KNOWN FAILURE MODES TO CHECK FOR:
${FAILURE_MODES.map((m, i) => `${i + 1}. ${m}`).join('\n')}

Judge: is every anchor present and identifiable by shape first? Are labels sparse, short, and correctly spelled? Is it one coherent scene (not a grid of panels)? Deduct for each failure mode you actually see.

Respond in EXACTLY this plain-text format, no markdown:
OVERALL_SCORE: <integer 0-100>
DECISION: <PASS | PASS_WITH_TEXT_RISK | FAIL>
ANCHORS_PRESENT: <integer>/<total ${anchors.length}>
MISSING_ANCHORS: <comma-separated anchor numbers, or none>
TOP_ISSUES: <up to 3 short phrases separated by "; ", or none>
REPAIR: <one or two sentences on the single highest-impact fix, or none>`;
  }

  function parseAudit(text) {
    const grab = (label) => {
      const m = String(text || '').match(new RegExp(`${label}:\\s*(.+)`, 'i'));
      return m ? m[1].trim() : '';
    };
    const scoreRaw = grab('OVERALL_SCORE').match(/\d+/);
    return {
      score: scoreRaw ? Math.max(0, Math.min(100, parseInt(scoreRaw[0], 10))) : null,
      decision: (grab('DECISION').match(/PASS_WITH_TEXT_RISK|PASS|FAIL/i) || [''])[0].toUpperCase(),
      anchorsPresent: grab('ANCHORS_PRESENT'),
      missing: grab('MISSING_ANCHORS'),
      issues: grab('TOP_ISSUES'),
      repair: grab('REPAIR'),
    };
  }

  function verdictClass(result) {
    if (result.score !== null && result.score >= TARGET_SCORE && result.decision === 'PASS') return 'audit-pass';
    if (result.decision === 'PASS_WITH_TEXT_RISK') return 'audit-warn';
    return 'audit-fail';
  }

  function verdictLabel(result) {
    if (result.score !== null && result.score >= TARGET_SCORE && result.decision === 'PASS') return `PASS · ${result.score}/100`;
    if (result.decision === 'PASS_WITH_TEXT_RISK') return `Pass with text risk · ${result.score ?? '?'}/100`;
    return `Below bar · ${result.score ?? '?'}/100 (need ${TARGET_SCORE})`;
  }

  function renderAudit(result) {
    const esc = window.escapeHtml || (window.MnemorizedUtils && window.MnemorizedUtils.escapeHtml) || (s => s);
    const missing = result.missing && !/^none$/i.test(result.missing) ? result.missing : '';
    const issues = result.issues && !/^none$/i.test(result.issues) ? result.issues : '';
    const repair = result.repair && !/^none$/i.test(result.repair) ? result.repair : '';
    setAuditMessage(`
      <div class="audit-summary ${verdictClass(result)}">
        <div class="audit-kicker">Image Quality Gate</div>
        <div class="audit-verdict">${esc(verdictLabel(result))}</div>
        <div class="audit-copy">Anchors detected: ${esc(result.anchorsPresent || '—')}</div>
        ${missing ? `<div class="audit-line">Missing anchors: ${esc(missing)}</div>` : ''}
        ${issues ? `<div class="audit-line">Top issues: ${esc(issues)}</div>` : ''}
        ${repair ? `<div class="audit-line audit-repair">Highest-impact fix: ${esc(repair)}</div>` : ''}
      </div>`);
  }

  async function runImageAudit() {
    const btn = document.getElementById('image-audit-btn');
    const imgSrc = finalImageSrc();
    if (!imgSrc) {
      setAuditMessage('<div class="audit-summary audit-warn"><div class="audit-copy">Generate a palace image first, then run the quality gate.</div></div>');
      return;
    }
    const story = (typeof currentStoryData !== 'undefined' && currentStoryData) || null;
    const anchors = story?.voLines || [];
    if (!anchors.length) {
      setAuditMessage('<div class="audit-summary audit-warn"><div class="audit-copy">No anchor script is loaded to audit against.</div></div>');
      return;
    }

    if (btn) { btn.disabled = true; btn.textContent = 'Auditing…'; }
    setAuditMessage('<div class="audit-summary"><div class="audit-copy">Scoring the image against the anchor list and failure modes…</div></div>');

    try {
      const imgRes = await fetch(imgSrc);
      const blob = await imgRes.blob();
      const base64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      });

      const body = {
        model: (typeof CLAUDE_MODEL !== 'undefined' ? CLAUDE_MODEL : 'claude-sonnet-4-6'),
        max_tokens: 700,
        messages: [{
          role: 'user',
          content: [
            { type: 'image', source: { type: 'base64', media_type: blob.type || 'image/png', data: base64 } },
            { type: 'text', text: buildAuditPrompt(anchors) },
          ],
        }],
      };

      const res = await claudeFetch(body, 'image-quality-audit');
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.error?.message || `Audit request failed (HTTP ${res.status}).`);
      }
      const data = await res.json();
      const text = (data.content || []).filter(b => b?.type === 'text').map(b => b.text).join('\n');
      const result = parseAudit(text);
      if (result.score === null && !result.decision) {
        throw new Error('Auditor returned an unreadable score.');
      }
      renderAudit(result);
    } catch (error) {
      setAuditMessage(`<div class="audit-summary audit-fail"><div class="audit-copy">Image audit failed: ${(window.escapeHtml || (s => s))(error.message)}</div></div>`);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '✦ Audit Image Quality (≥96 gate)'; }
    }
  }

  window.MnemorizedImageAudit = { runImageAudit, TARGET_SCORE };
  window.runForgeImageAudit = runImageAudit;
})();
