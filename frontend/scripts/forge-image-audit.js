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

  // CANONICAL RUBRIC — mirror of docs/image-scoring-rubric.md. This is the single
  // scoring standard shared with the offline QA tools; keep the two in sync. The
  // score is deterministic: six weighted categories (sum 100) minus per-defect
  // deductions, then capped by any triggered hard gate. OVERALL = min(RAW, caps).
  const RUBRIC = `SCORING METHOD (deterministic — you MUST show the arithmetic):
1. Start each category at its full value. Subtract the per-defect deductions.
2. RAW_SUM = sum of the six categories (max 100).
3. Apply every triggered HARD GATE: each gate caps OVERALL (it does not subtract).
4. OVERALL_SCORE = min(RAW_SUM, lowest triggered gate cap), rounded to an integer.
When torn between two scores, choose the LOWER.

CATEGORIES (weights sum to 100):
A. Anchor Completeness — 30. −10 per absent/unidentifiable anchor; −5 per anchor
   too tiny/crowded to read; −3 per anchor identifiable ONLY by an attached label.
B. Hook Fidelity — 20. −8 per anchor rendered as TEXT SLAPPED ON A GENERIC PROP
   (barrel/wall/crate/plaque) when a sanctioned metaphor existed (banana=potassium,
   salt shaker=sodium, box of baking soda=bicarbonate, skull=toxicity, hourglass=
   time, turtle=slow, padlock=restricted…); −4 per weak/arbitrary object with no
   association; −2 per anchor using a weaker tier than warranted. Do NOT penalize a
   correct functional/contrast hook on a threshold DECISION (e.g. traffic-light=K+).
C. Silhouette & Legibility — 15. −5 illegible clutter; −4 duplicated identical
   silhouettes; −3 reading path lost to busyness.
D. Text Discipline — 15. −6 per misspelled/invented required label; −5 meta-
   instruction/caption/zone-name text leaked into the image; −3 per crammed multi-
   line label list; −2 per needless label the metaphor already carried.
E. Medical Fidelity — 10. −10 an implied fact/threshold is WRONG; −4 ambiguous dose.
F. Scene Coherence — 10. −6 segmented grid/booths/panels instead of one scene; −3
   incoherent floating placement. A deliberately off-theme sanctioned metaphor is NOT
   a coherence defect (bizarreness effect is intended).

HARD GATES (cap OVERALL; use the lowest triggered cap):
G1: 1 anchor missing→cap 79; 2 missing→cap 70; 3+ missing→cap 55.
G2: any misspelled/invented required label→cap 88.
G3: meta-instruction/caption/zone text leaked into image→cap 85.
G4: segmented grid/booths/panels instead of one scene→cap 80.
G5: any medically wrong fact/threshold implied→cap 75.
G6: any anchor encoded ONLY as text on a generic prop (no visual hook) when a
    sanctioned metaphor/stronger hook existed→cap 90.

DECISION: PASS = OVERALL>=96 AND no G1/G2/G5. PASS_WITH_TEXT_RISK = OVERALL>=90,
no G1/G5, but G2/G3/G6 present. REPAIR = 70..95 with a bounded fixable defect.
REGENERATE = OVERALL<70 or 2+ anchors missing. Never PASS if any anchor is missing.

ANTI-INFLATION: a label alone never satisfies an anchor (needs shape/interaction/
placement); treat labels as unreliable unless legible AND correctly spelled; do not
invent anchors that are not visible; formulas allowed only attached to a visible
device. On a plate with >8 anchors, re-verify before claiming all present.`;

  // Gate cap lookup used to recompute OVERALL client-side so the model's arithmetic
  // cannot drift above what its own gate list allows.
  const GATE_CAPS = { G2: 88, G3: 85, G4: 80, G5: 75, G6: 90 };
  function g1Cap(missingCount) {
    if (missingCount >= 3) return 55;
    if (missingCount === 2) return 70;
    if (missingCount === 1) return 79;
    return 100;
  }

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
    return `You are an exacting external visual-mnemonic image auditor. Score the attached memory-palace illustration against the anchor list using the CANONICAL RUBRIC below. Never inflate; a genuinely publishable board-study plate scores >=${TARGET_SCORE}.

ANCHORS THAT SHOULD APPEAR (each must be a recognizable visual, readable at normal size):
${anchorLines}

${RUBRIC}

Respond in EXACTLY this plain-text format, no markdown, and make OVERALL_SCORE equal min(RAW_SUM, lowest gate cap):
OVERALL_SCORE: <integer 0-100>
DECISION: <PASS | PASS_WITH_TEXT_RISK | REPAIR | REGENERATE>
CATEGORY_SCORES: A:<0-30> B:<0-20> C:<0-15> D:<0-15> E:<0-10> F:<0-10>
RAW_SUM: <integer 0-100>
GATES_TRIGGERED: <e.g. "G1(1 missing) cap79; G6 cap90" or "none">
ANCHORS_PRESENT: <integer>/<total ${anchors.length}>
MISSING_ANCHORS: <comma-separated anchor numbers, or none>
TOP_ISSUES: <up to 3 short phrases separated by "; ", or none>
REPAIR: <one or two sentences on the single highest-impact fix, or none>`;
  }

  function countMissing(missingStr) {
    if (!missingStr || /^none$/i.test(missingStr)) return 0;
    return missingStr.split(',').map(s => s.trim()).filter(Boolean).length;
  }

  // Recompute OVERALL = min(RAW_SUM, every triggered gate cap) from the fields the
  // model reported, so a model that writes an inflated OVERALL is pulled back down
  // to what its own RAW_SUM, missing-anchor count, and gate list actually permit.
  function enforceScore(modelScore, rawSum, gatesStr, missingCount) {
    const caps = [];
    if (Number.isFinite(rawSum)) caps.push(rawSum);
    caps.push(g1Cap(missingCount));
    const gatesUpper = String(gatesStr || '').toUpperCase();
    Object.keys(GATE_CAPS).forEach(g => { if (gatesUpper.includes(g)) caps.push(GATE_CAPS[g]); });
    const enforced = Math.min(...caps);
    // If we have no RAW_SUM and no gates, fall back to the model's own number.
    if (!Number.isFinite(rawSum) && caps.length <= 1 && Number.isFinite(modelScore)) return modelScore;
    return Math.max(0, Math.min(100, Math.round(enforced)));
  }

  function decisionFor(score, gatesStr, missingCount) {
    const g = String(gatesStr || '').toUpperCase();
    const hasG1 = missingCount >= 1 || g.includes('G1');
    const hasG5 = g.includes('G5');
    const textRisk = g.includes('G2') || g.includes('G3') || g.includes('G6');
    if (score >= TARGET_SCORE && !hasG1 && !g.includes('G2') && !hasG5) return 'PASS';
    if (score >= 90 && !hasG1 && !hasG5 && textRisk) return 'PASS_WITH_TEXT_RISK';
    if (score < 70 || missingCount >= 2) return 'REGENERATE';
    return 'REPAIR';
  }

  function parseAudit(text) {
    const grab = (label) => {
      const m = String(text || '').match(new RegExp(`${label}:\\s*(.+)`, 'i'));
      return m ? m[1].trim() : '';
    };
    const modelScoreM = grab('OVERALL_SCORE').match(/\d+/);
    const modelScore = modelScoreM ? Math.max(0, Math.min(100, parseInt(modelScoreM[0], 10))) : null;
    const rawSumM = grab('RAW_SUM').match(/\d+/);
    const rawSum = rawSumM ? parseInt(rawSumM[0], 10) : NaN;
    const gates = grab('GATES_TRIGGERED');
    const missing = grab('MISSING_ANCHORS');
    const missingCount = countMissing(missing);
    const categories = grab('CATEGORY_SCORES');
    // Readable only if the model actually returned a score or a breakdown; without
    // any of these, treat the response as unparseable rather than defaulting to 100.
    const readable = modelScore !== null || Number.isFinite(rawSum) || !!categories;
    const score = readable ? enforceScore(modelScore, rawSum, gates, missingCount) : null;
    return {
      score,
      modelScore,
      rawSum: Number.isFinite(rawSum) ? rawSum : null,
      // Trust the deterministic decision derived from the enforced score + gates,
      // not the model's free-text DECISION line.
      decision: readable ? decisionFor(score, gates, missingCount) : '',
      categories,
      gates: gates && !/^none$/i.test(gates) ? gates : '',
      anchorsPresent: grab('ANCHORS_PRESENT'),
      missing,
      issues: grab('TOP_ISSUES'),
      repair: grab('REPAIR'),
    };
  }

  function verdictClass(result) {
    if (result.decision === 'PASS' && result.score >= TARGET_SCORE) return 'audit-pass';
    if (result.decision === 'PASS_WITH_TEXT_RISK') return 'audit-warn';
    return 'audit-fail';
  }

  function verdictLabel(result) {
    const s = result.score ?? '?';
    if (result.decision === 'PASS' && result.score >= TARGET_SCORE) return `PASS · ${s}/100`;
    if (result.decision === 'PASS_WITH_TEXT_RISK') return `Pass with text risk · ${s}/100`;
    if (result.decision === 'REGENERATE') return `Regenerate · ${s}/100 (need ${TARGET_SCORE})`;
    return `Repair · ${s}/100 (need ${TARGET_SCORE})`;
  }

  function renderAudit(result) {
    const esc = window.escapeHtml || (window.MnemorizedUtils && window.MnemorizedUtils.escapeHtml) || (s => s);
    const missing = result.missing && !/^none$/i.test(result.missing) ? result.missing : '';
    const issues = result.issues && !/^none$/i.test(result.issues) ? result.issues : '';
    const repair = result.repair && !/^none$/i.test(result.repair) ? result.repair : '';
    const categories = result.categories ? String(result.categories) : '';
    const gates = result.gates ? String(result.gates) : '';
    const rawNote = (result.rawSum !== null && result.rawSum !== result.score)
      ? ` (raw ${result.rawSum}, capped by gate)` : '';
    setAuditMessage(`
      <div class="audit-summary ${verdictClass(result)}">
        <div class="audit-kicker">Image Quality Gate</div>
        <div class="audit-verdict">${esc(verdictLabel(result))}${esc(rawNote)}</div>
        <div class="audit-copy">Anchors detected: ${esc(result.anchorsPresent || '—')}</div>
        ${categories ? `<div class="audit-line">Breakdown: ${esc(categories)}</div>` : ''}
        ${gates ? `<div class="audit-line">Gates: ${esc(gates)}</div>` : ''}
        ${missing ? `<div class="audit-line">Missing anchors: ${esc(missing)}</div>` : ''}
        ${issues ? `<div class="audit-line">Top issues: ${esc(issues)}</div>` : ''}
        ${repair ? `<div class="audit-line audit-repair">Highest-impact fix: ${esc(repair)}</div>` : ''}
      </div>`);
  }

  // Core scoring: fetch the image bytes, send them + the anchor list to the vision
  // auditor, and return the parsed/gate-enforced result. Pure of DOM button state so
  // both the manual button and the auto-retry loop can reuse it. Throws on hard error.
  async function performAudit(anchors, imgSrc) {
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
    return result;
  }

  function currentAnchors() {
    const story = (typeof currentStoryData !== 'undefined' && currentStoryData) || null;
    return story?.voLines || [];
  }

  async function runImageAudit() {
    const btn = document.getElementById('image-audit-btn');
    const imgSrc = finalImageSrc();
    if (!imgSrc) {
      setAuditMessage('<div class="audit-summary audit-warn"><div class="audit-copy">Generate a palace image first, then run the quality gate.</div></div>');
      return;
    }
    const anchors = currentAnchors();
    if (!anchors.length) {
      setAuditMessage('<div class="audit-summary audit-warn"><div class="audit-copy">No anchor script is loaded to audit against.</div></div>');
      return;
    }

    if (btn) { btn.disabled = true; btn.textContent = 'Auditing…'; }
    setAuditMessage('<div class="audit-summary"><div class="audit-copy">Scoring the image against the anchor list and failure modes…</div></div>');

    try {
      const result = await performAudit(anchors, imgSrc);
      renderAudit(result);
    } catch (error) {
      setAuditMessage(`<div class="audit-summary audit-fail"><div class="audit-copy">Image audit failed: ${(window.escapeHtml || (s => s))(error.message)}</div></div>`);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '✦ Audit Image Quality (≥96 gate)'; }
    }
  }

  // ── Audit → auto-retry loop ─────────────────────────────────────
  // Turn the one-shot gate into a closed loop: audit the current image; if it does
  // not PASS, feed the auditor's own repair note back into the image prompt, call the
  // existing generateImages() to re-render, and re-audit — up to maxRepairs times.
  // Deterministically keeps the highest-scoring render across attempts. Opt-in
  // (its own button) because each pass spends a paid image + audit request, per the
  // session cost protocol.
  const MAX_REPAIRS_DEFAULT = 1;

  // Build a bounded repair directive from the auditor's structured verdict.
  function buildRepairDirective(result) {
    const parts = [];
    if (result.missing && !/^none$/i.test(result.missing)) {
      parts.push(`These anchors are missing or unclear — add each, drawn exactly once: ${result.missing}.`);
    }
    const gates = String(result.gates || '').toUpperCase();
    if (gates.includes('G3')) parts.push('Remove any leaked caption, zone-name, or meta-instruction text.');
    if (gates.includes('G4')) parts.push('Render one single coherent scene, not a grid of panels.');
    if (gates.includes('G2') || gates.includes('G6')) parts.push('Do not draw numbers/formulas as text; leave their signpost surfaces blank.');
    if (result.repair && !/^none$/i.test(result.repair)) parts.push(result.repair);
    const body = (parts.join(' ') || 'Improve anchor clarity and reduce clutter.').slice(0, 220);
    return `REPAIR PASS — fix the single highest-impact defect while keeping every other anchor unchanged: ${body}`;
  }

  // Insert the repair directive just BEFORE the whitelist fence (so both the anchor
  // list and the fence survive the length clamp, which trims from the tail).
  function injectRepair(prompt, directive) {
    const base = String(prompt || '');
    const marker = 'RENDERABLE TEXT ALLOWLIST';
    const idx = base.indexOf(marker);
    if (idx >= 0) return `${base.slice(0, idx)}${directive}\n\n${base.slice(idx)}`;
    return `${base.replace(/\s+$/, '')}\n\n${directive}`;
  }

  async function autoAuditRetry(opts) {
    const maxRepairs = (opts && Number.isInteger(opts.maxRepairs)) ? opts.maxRepairs : MAX_REPAIRS_DEFAULT;
    const btn = document.getElementById('image-audit-retry-btn');
    const auditBtn = document.getElementById('image-audit-btn');
    const anchors = currentAnchors();
    if (!finalImageSrc()) {
      setAuditMessage('<div class="audit-summary audit-warn"><div class="audit-copy">Generate a palace image first, then run auto-retry.</div></div>');
      return;
    }
    if (!anchors.length) {
      setAuditMessage('<div class="audit-summary audit-warn"><div class="audit-copy">No anchor script is loaded to audit against.</div></div>');
      return;
    }

    const p2el = document.getElementById('prompt-copy-2');
    const p2panel = document.getElementById('img-prompt-2');
    const basePrompt2 = p2el ? p2el.value : '';

    if (btn) { btn.disabled = true; btn.textContent = 'Auto-forging…'; }
    if (auditBtn) auditBtn.disabled = true;

    let best = null; // { score, decision, result }
    let attemptsRun = 0;
    try {
      for (let attempt = 0; attempt <= maxRepairs; attempt++) {
        const imgSrc = finalImageSrc();
        if (!imgSrc) break;
        attemptsRun = attempt + 1;
        setAuditMessage(`<div class="audit-summary"><div class="audit-copy">Auto-retry pass ${attempt + 1}/${maxRepairs + 1}: scoring the current render…</div></div>`);

        const result = await performAudit(anchors, imgSrc);
        if (!best || (result.score ?? 0) > (best.score ?? 0)) {
          best = { score: result.score ?? 0, decision: result.decision, result };
        }
        renderAudit(result);

        if (result.decision === 'PASS') break;
        if (attempt === maxRepairs) break;

        // Feed the repair note back into prompt 2 and re-render.
        if (p2el) {
          const repaired = injectRepair(basePrompt2, buildRepairDirective(result));
          p2el.value = repaired;
          if (p2panel) p2panel.textContent = repaired;
        }
        setAuditMessage(`<div class="audit-summary"><div class="audit-copy">Below ${TARGET_SCORE}. Regenerating with a targeted repair (pass ${attempt + 2}/${maxRepairs + 1})…</div></div>`);
        const before = finalImageSrc();
        if (typeof generateImages === 'function') {
          await generateImages();
        } else {
          break;
        }
        // If no fresh image landed (backend guard, error, quota), stop looping.
        if (finalImageSrc() === before) break;
      }

      // Restore the operator's base prompt so a lingering repair note does not leak
      // into the next manual regenerate.
      if (p2el) { p2el.value = basePrompt2; if (p2panel) p2panel.textContent = basePrompt2; }

      if (best) {
        renderAudit(best.result);
        const passed = best.decision === 'PASS' && (best.score ?? 0) >= TARGET_SCORE;
        const note = passed
          ? `Reached PASS in ${attemptsRun} pass${attemptsRun !== 1 ? 'es' : ''}.`
          : `Best after ${attemptsRun} pass${attemptsRun !== 1 ? 'es' : ''}: ${best.score}/100 — needs a manual repair.`;
        const el = auditResultEl();
        if (el) {
          const div = document.createElement('div');
          div.className = 'audit-line';
          div.style.marginTop = '8px';
          div.textContent = `Auto-retry: ${note}`;
          el.querySelector('.audit-summary')?.appendChild(div);
        }
      }
    } catch (error) {
      if (p2el) { p2el.value = basePrompt2; if (p2panel) p2panel.textContent = basePrompt2; }
      setAuditMessage(`<div class="audit-summary audit-fail"><div class="audit-copy">Auto-retry failed: ${(window.escapeHtml || (s => s))(error.message)}</div></div>`);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '✦ Auto-forge to ≥96'; }
      if (auditBtn) auditBtn.disabled = false;
    }
  }

  window.MnemorizedImageAudit = { runImageAudit, performAudit, autoAuditRetry, TARGET_SCORE };
  window.runForgeImageAudit = runImageAudit;
  window.runForgeAutoRetry = autoAuditRetry;
})();
