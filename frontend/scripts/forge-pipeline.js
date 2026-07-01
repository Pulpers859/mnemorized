// ══════════════════════════════════════════════════
// FORGE PIPELINE — constants, config UI, main pipeline
// Depends on: forge-state.js, forge-auth.js, forge-upload.js
// ══════════════════════════════════════════════════

// ── Shared constants ─────────────────────────────────────────────

const SKETCHY_STYLE = 'Hand-drawn 2D cartoon illustration drawn with Micron pens and Copic markers on paper then scanned. ' +
  'Wobbly, imperfect ink outlines with visible line weight variation — thick at corners, thin on straights, ' +
  'slightly unsteady like a real human hand drew every line. NO clean digital vector lines. ' +
  'Cell-shaded flat coloring: each surface has ONE base color and ONE shadow color with a HARD crisp edge, ' +
  'like coloring with markers that leave visible fill strokes. NO soft gradients, NO airbrush, NO blending. ' +
  'Limited muted earth-tone palette, maximum 5 colors plus black. ' +
  'Characters are angular cartoon caricatures with big heads, pointy chins, exaggerated expressions — ' +
  'like editorial newspaper cartoons, NOT anime, NOT 3D, NOT realistic proportions. ' +
  'Backgrounds filled with hand-drawn linework, cross-hatching, and flat marker fills. ' +
  'NO gradient fills, NO atmospheric haze, NO depth of field blur. ' +
  'Flat even lighting — NO spotlight cones, NO volumetric light, NO lens flares, NO glowing effects. ' +
  'All text in the scene looks hand-written with a marker, slightly uneven and imperfect. ' +
  'Every object looks like it was drawn on a whiteboard or poster board with markers. ' +
  'Style reference: Sketchy Medical, Pixorize, editorial cartoon, medical education poster drawn by hand.';

const ANTI_META_TEXT = 'TEXT RULES: Do NOT render any floating labels, zone names, category descriptions, ' +
  'or meta-commentary as visible text in the image. The ONLY text that should appear is text that is ' +
  'physically part of an object in the scene — written on signs, sticky notes, labels, screens, bottles, ' +
  'chalkboards, or other in-world surfaces. No floating captions. No zone labels. No anchor descriptions.';

const ZONE_CYCLE = [
  'FAR LEFT', 'LEFT', 'CENTER LEFT', 'CENTER', 'CENTER RIGHT', 'RIGHT',
  'FAR RIGHT', 'FOREGROUND LEFT', 'FOREGROUND CENTER', 'FOREGROUND RIGHT',
  'BACKGROUND LEFT', 'BACKGROUND CENTER', 'BACKGROUND RIGHT', 'BACKGROUND CORNER', 'DOORWAY'
];

function buildAnchorLines(anchors) {
  return anchors.map(v => `  (${v.zone.toLowerCase()}) Anchor ${v.n}: ${v.visual}`).join('\n');
}

// ── Demo data ────────────────────────────────────────────────────

const DEMO_DATA = {
  clinical_context: {
    core_concepts: `1. DKA diagnostic triad: hyperglycemia (>250 mg/dL), anion gap metabolic acidosis (pH <7.3, bicarb <18), ketonemia/ketonuria
2. Fluid resuscitation first: 1-2L NS bolus in first hour, then 250-500 mL/hr; switch to D5 1/2NS when glucose <200
3. Insulin drip: 0.1-0.14 units/kg/hr — do NOT bolus; do NOT start until K+ ≥3.3
4. Potassium replacement: if K+ <3.3, hold insulin and replete aggressively; if 3.3-5.3, add 20-40 mEq/L to each liter of IVF
5. Monitor anion gap closure, NOT glucose, to determine resolution — gap closes before glucose normalizes
6. Cerebral edema risk in pediatrics with overly aggressive fluid resuscitation or rapid glucose drops`,
    scene_logic: `Guide character stands center frame at an IV pole. Left side: diagnostic triad elements (glucose meter, pH strip, ketone test). Center: fluid bags and insulin drip. Right side: potassium bottles arranged by threshold values. Foreground: anion gap monitor. Background: pediatric warning sign.`
  },
  scene_title: 'The Midnight Drip Bar',
  opening: 'Welcome to the Midnight Drip Bar — a dimly lit speakeasy where every drink is an IV bag and the bartender is a burned-out ER attending who exclusively serves fluids based on lab values. The neon sign above the bar flickers between "OPEN" and "ANION GAP: 24." The whole place smells like normal saline and regret. Our bartender stands behind the counter, one hand on an IV pole, the other pointing at a chalkboard menu that lists fluids by potassium level. Let\'s walk through how this attending runs a DKA resuscitation — one drip at a time.',
  voLines: [
    {
      n: 1,
      narration: 'Take a look at the neon sign above the entrance. You can see three numbers glowing in red: 250, 7.3, and 18. These are your DKA diagnostic thresholds — glucose above 250, pH below 7.3, and bicarb below 18. Notice how the sign also shows the word "GAP" buzzing in and out. That\'s your anion gap metabolic acidosis. All three need to be present. Get it? Three numbers on the sign, three criteria for the diagnosis.',
      visual: 'A flickering neon bar sign above the entrance displaying "250 | 7.3 | 18" in red with the word "GAP" buzzing intermittently below — three glowing diagnostic thresholds',
      anchor: 'DKA diagnostic triad: glucose >250 mg/dL, pH <7.3, bicarb <18 mEq/L, plus anion gap metabolic acidosis'
    },
    {
      n: 2,
      narration: 'Now look at the bartender — our attending — pouring from a massive jug labeled "NS" into two enormous pint glasses. Notice the clock on the wall behind them reads "HOUR 1" and the glasses are marked "1L" each. That\'s your initial fluid resuscitation: 1 to 2 liters of normal saline bolused in the first hour. Fluids come first in DKA. Before insulin, before anything else. The body is profoundly volume depleted — sometimes 6 to 9 liters down.',
      visual: 'The bartender (ER attending in scrubs) pouring from a giant jug labeled "NS" into two oversized pint glasses each marked "1L", with a wall clock showing "HOUR 1" behind them',
      anchor: 'Initial fluid resuscitation: 1-2L normal saline bolus in the first hour; fluids before insulin; patients are 6-9L volume depleted'
    },
    {
      n: 3,
      narration: 'Over on the left side of the bar, notice the shelf of smaller bottles. There\'s a bottle labeled "D5 ½NS" with a sticky note that says "WHEN GLUCOSE < 200." This is your fluid switch point. Once the blood glucose drops below 200, you don\'t stop fluids — you switch to dextrose-containing fluids. This prevents hypoglycemia while you keep the insulin drip running to close the anion gap. The gap is what matters, not the glucose number.',
      visual: 'A bar shelf on the left holding a bottle labeled "D5 ½NS" with a prominent sticky note reading "WHEN GLUCOSE < 200" in red marker — the fluid switch point',
      anchor: 'Switch to D5 ½NS when glucose <200 mg/dL — continue insulin to close anion gap, add dextrose to prevent hypoglycemia'
    },
    {
      n: 4,
      narration: 'Right here behind the bar, look at the IV pump mounted on the central pole. The rate display reads "0.1 units/kg/hr" and there\'s a big red sticker that says "NO BOLUS." That\'s your insulin drip protocol. You start at 0.1 to 0.14 units per kg per hour — continuous infusion, no bolus. The bolus was removed from modern protocols because it increases hypoglycemia and hypokalemia risk without improving outcomes. Just the drip.',
      visual: 'An IV pump mounted on a central pole displaying "0.1 units/kg/hr" with a large red circular sticker reading "NO BOLUS" — the insulin drip protocol station',
      anchor: 'Insulin drip: 0.1-0.14 units/kg/hr continuous infusion; do NOT give insulin bolus — increases hypoglycemia and hypokalemia risk'
    },
    {
      n: 5,
      narration: 'Now this is critical — look at the three potassium bottles lined up on the right side of the bar. They\'re color-coded like a traffic light. The red one says "K < 3.3 — HOLD INSULIN." The yellow one says "K 3.3-5.3 — add 20-40 mEq/L." The green one says "K > 5.3 — recheck in 2 hrs." This is the single most dangerous part of DKA management. If you start insulin when potassium is below 3.3, you will drive it further down and cause fatal arrhythmias. Always check potassium before starting the drip.',
      visual: 'Three potassium bottles on the right bar shelf, traffic-light colored: RED labeled "K<3.3 HOLD INSULIN", YELLOW labeled "K 3.3-5.3 Add 20-40mEq", GREEN labeled "K>5.3 Recheck 2hr" — the potassium decision tree',
      anchor: 'Potassium protocol: K<3.3 = hold insulin and replete aggressively; K 3.3-5.3 = add 20-40 mEq/L to IVF; K>5.3 = recheck in 2 hours'
    },
    {
      n: 6,
      narration: 'Finally, notice the chalkboard behind the bartender. At the top it says "CLOSING TIME" and underneath there\'s a drawing of an anion gap graph trending downward — NOT a glucose graph. This is how you know DKA is resolving. You follow the anion gap, not the glucose. The glucose will normalize first, but if the gap is still open, the patient is still in DKA. Resolution means: gap closed, pH above 7.3, bicarb above 18, and the patient can eat. Then you overlap subcutaneous insulin 2 hours before stopping the drip.',
      visual: 'A large chalkboard behind the bar reading "CLOSING TIME" at the top with a hand-drawn anion gap graph trending down, the word "GLUCOSE" crossed out, and a checklist: "Gap closed ✓ pH>7.3 ✓ Bicarb>18 ✓ Eating ✓ → Overlap SQ 2hr"',
      anchor: 'Monitor anion gap (not glucose) for DKA resolution; resolution = gap closed + pH>7.3 + bicarb>18 + tolerating PO; overlap SQ insulin 2hr before stopping drip'
    },
    {
      n: 7,
      narration: 'Now look at the jukebox in the far left corner. Instead of song titles, the playlist shows the 5 I\'s — Infection, Insulin noncompliance, Ischemia, Intoxication, and Iatrogenic. These are the five most common precipitants of DKA. The number one cause? Infection. Number two? Insulin noncompliance — the patient stopped taking their insulin. Every DKA workup should include a search for the trigger. Get it? The jukebox plays what started this whole episode.',
      visual: 'A retro jukebox in the far left corner with a playlist display showing five song titles: "1. Infection", "2. Insulin Noncompliance", "3. Ischemia", "4. Intoxication", "5. Iatrogenic" — the 5 I\'s of DKA precipitants',
      anchor: 'DKA precipitants (5 I\'s): Infection (#1 cause), Insulin noncompliance (#2), Ischemia, Intoxication, Iatrogenic'
    },
    {
      n: 8,
      narration: 'Over by the bathroom door, notice the sign that says "NO BICARB ZONE" with a pH threshold of 6.9 written below it. Here\'s the rule: do NOT give bicarbonate in DKA unless the pH is below 6.9. Above 6.9, the acidosis will correct itself once you close the anion gap with insulin and fluids. Giving bicarb when it\'s not needed can worsen hypokalemia and paradoxically worsen CNS acidosis. The only exception is that critical pH below 6.9 where cardiac function is at risk.',
      visual: 'A bathroom door with a large prohibition-style sign reading "NO BICARB ZONE" and below it "Unless pH < 6.9" in red — the bicarbonate threshold rule',
      anchor: 'Do NOT give bicarbonate unless pH <6.9 — bicarb worsens hypokalemia and paradoxical CNS acidosis; acidosis self-corrects with insulin and fluids'
    },
    {
      n: 9,
      narration: 'Take a look at the small VIP table in the foreground — there\'s a child-sized chair with a warning sign that says "SLOW DOWN" and a brain icon with swelling arrows. This is your cerebral edema warning. In pediatric DKA, overly aggressive fluid resuscitation or dropping the glucose too fast can cause fatal cerebral edema. The rule: don\'t drop glucose faster than 50 to 75 mg/dL per hour in kids. This is the number one cause of death in pediatric DKA — not the acidosis itself.',
      visual: 'A small VIP table in the foreground with a child-sized chair, a warning placard reading "SLOW DOWN — 50-75/hr MAX" and a cartoon brain icon with red swelling arrows — the pediatric cerebral edema warning',
      anchor: 'Pediatric DKA: cerebral edema is #1 cause of death; do not drop glucose >50-75 mg/dL/hr; avoid overly aggressive fluid resuscitation in children'
    },
    {
      n: 10,
      narration: 'Finally, check out the tip jar at the end of the bar. It\'s labeled "BHB > Urine Ketones" and there\'s a note taped to it that says "UA lies." This is a clinical pearl most people miss. Urine ketones measure acetoacetate, but in DKA the predominant ketone is beta-hydroxybutyrate. As the patient improves, BHB converts to acetoacetate — so urine ketones can actually increase as the patient gets better. That\'s why you follow the serum BHB or the anion gap, never the urine dipstick, to track resolution.',
      visual: 'A glass tip jar at the far end of the bar labeled "BHB > Urine Ketones" with a sticky note reading "UA lies — ketones rise as patient improves" — the beta-hydroxybutyrate monitoring pearl',
      anchor: 'Follow serum beta-hydroxybutyrate (BHB) or anion gap, NOT urine ketones — urine acetoacetate rises paradoxically during DKA treatment as BHB converts'
    }
  ],
  review_script: `When you see the neon sign with 250, 7.3, and 18 — remember the DKA diagnostic triad: glucose >250, pH <7.3, bicarb <18 with anion gap acidosis.
When you see the bartender pouring two 1L pint glasses of NS — remember fluids first, 1-2L NS in hour one, before insulin.
When you see the D5 ½NS bottle with the "glucose <200" note — remember to switch fluids when glucose drops below 200 to prevent hypoglycemia while closing the gap.
When you see the IV pump reading 0.1 units/kg/hr with the "NO BOLUS" sticker — remember insulin drip only, no bolus, 0.1-0.14 units/kg/hr.
When you see the three traffic-light potassium bottles — remember K<3.3 means hold insulin, K 3.3-5.3 means add 20-40 mEq, K>5.3 means recheck.
When you see the chalkboard showing anion gap trending down with "GLUCOSE" crossed out — remember to follow the gap, not glucose, for resolution.
When you see the jukebox playing the 5 I's — remember DKA precipitants: Infection, Insulin noncompliance, Ischemia, Intoxication, Iatrogenic.
When you see the "NO BICARB ZONE" bathroom sign with pH 6.9 — remember do not give bicarbonate unless pH <6.9.
When you see the child-sized VIP chair with "SLOW DOWN" and the swelling brain — remember pediatric cerebral edema risk, don't drop glucose >50-75/hr.
When you see the tip jar labeled "BHB > Urine Ketones" — remember follow serum BHB or anion gap, not urine ketones, which rise paradoxically during treatment.`,
  prompt1_sample: 'Dimly lit speakeasy bar interior at night, warm amber and deep teal muted palette, neon signage casting colored glow, burned-out ER attending character standing center frame behind a bar counter with IV poles instead of beer taps, shelves of IV fluid bags and medicine bottles lining the back wall, chalkboard menu visible in background, wide establishing shot showing full room layout with clear zones far left left center right far right foreground background, enough space for 8-10 distinct labeled medical objects'
};

// ── Demo / operator toggles ──────────────────────────────────────

const demoToggle = document.getElementById('demo-mode-toggle');
const demoBanner = document.getElementById('demo-banner');
demoToggle.addEventListener('change', () => {
  demoBanner.classList.toggle('visible', demoToggle.checked);
});

const operatorToggle = document.getElementById('operator-toggle');
const operatorPanel = document.getElementById('operator-panel');

let operatorUnlocked = false;

async function checkOperatorCode(input) {
  const data = new TextEncoder().encode(input || '');
  const hash = await crypto.subtle.digest('SHA-256', data);
  const hex = [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, '0')).join('');
  return hex === '71b41d6dd48dc58eba8f5cf9edf30fef6597fdf285a521bb8fcbad4b3d50887d';
}

operatorToggle.addEventListener('change', async () => {
  if (operatorToggle.checked && !operatorUnlocked) {
    const code = prompt('Enter operator access code:');
    if (!(await checkOperatorCode(code))) {
      operatorToggle.checked = false;
      return;
    }
    operatorUnlocked = true;
  }
});

operatorToggle.addEventListener('change', () => {
  if (operatorUnlocked) {
    operatorPanel.classList.toggle('visible', operatorToggle.checked);
  }
});

function isDemoMode() { return demoToggle.checked; }
function isOperatorMode() { return operatorToggle.checked; }
function demoDelay(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Copy helpers ─────────────────────────────────────────────────

function copyAllTSV() {
  const topic = document.getElementById('topic')?.value?.trim() || '';
  const p1 = document.getElementById('prompt-copy-1')?.value || '';
  const p2 = document.getElementById('prompt-copy-2')?.value || '';
  const clean = s => s.replace(/[\t\n\r]/g, ' ');
  const tsv = [clean(topic), clean(p1), clean(p2)].join('\t');
  const btn = document.getElementById('copy-all-tsv');
  copyToClipboard(tsv, btn, 'Copy All → Spreadsheet');
}

function copyVoScript() {
  const rows = [...document.querySelectorAll('#vo-body tr')];
  const sceneTitle = document.querySelector('.story-scene-title')?.textContent || '';
  const opening = document.querySelector('.story-opening')?.innerText?.trim() || '';
  const header = `SCENE: ${sceneTitle}\n\n${opening}\n\n`;
  const lines = rows.map((row, i) => {
    const cells = row.querySelectorAll('td');
    const narClone = cells[0]?.cloneNode(true);
    narClone?.querySelectorAll('.row-num').forEach(el => el.remove());
    const narration = narClone?.innerText?.trim() || '';
    const visual    = cells[1]?.textContent?.trim() || '';
    const encodes   = cells[2]?.textContent?.trim() || '';
    return `[${i+1}] NARRATION: ${narration}\n    VISUAL: ${visual}\n    ENCODES: ${encodes}`;
  }).join('\n\n');
  const full = header + lines + '\n\n── RAPID REVIEW ──\n' + (document.getElementById('review-text')?.innerText || '');
  const btn = document.getElementById('copy-vo-btn');
  copyToClipboard(full, btn, 'Copy Full Script');
}

function copyNarrationOnly() {
  const rows  = [...document.querySelectorAll('#vo-body tr')];
  const title = document.querySelector('.story-scene-title')?.textContent || '';
  const opening = document.querySelector('.story-opening')?.innerText?.trim() || '';

  const lines = rows.map(row => {
    const cell  = row.querySelectorAll('td')[0];
    const clone = cell.cloneNode(true);
    clone.querySelectorAll('.row-num').forEach(el => el.remove());
    return clone.innerText.trim()
      .replace(/\[PAUSE\]/gi, '...')
      .replace(/\[BEAT\]/gi,  '...')
      .replace(/\[EMPHASIS:\s*([^\]]+)\]/gi, '$1')
      .trim();
  }).filter(Boolean);

  const script = `${title}\n\n${opening}\n\n${lines.join('\n\n')}`;
  const btn = document.getElementById('copy-narration-btn');
  copyToClipboard(script, btn, 'Copy Narration Only');
}

function copyPrompt(n) {
  const src = document.getElementById(`prompt-copy-${n}`);
  const btn = document.getElementById(`copy-prompt-${n}`);
  if (!src || !btn) return;
  copyToClipboard(src.value, btn, `Copy Prompt ${n}`);
}

// ── Config UI ────────────────────────────────────────────────────

function setupSelectCustom(selectId, customFieldId) {
  const sel = document.getElementById(selectId);
  const field = document.getElementById(customFieldId);
  sel.addEventListener('change', () => {
    field.style.display = sel.value === 'custom' ? 'block' : 'none';
  });
}
setupSelectCustom('setting-select', 'custom-setting');
setupSelectCustom('guide-select', 'custom-guide');

document.querySelectorAll('#tone-chips .chip').forEach(chip => {
  function selectChip() {
    document.querySelectorAll('#tone-chips .chip').forEach(c => {
      c.classList.remove('active');
      c.setAttribute('aria-checked', 'false');
    });
    chip.classList.add('active');
    chip.setAttribute('aria-checked', 'true');
  }
  chip.addEventListener('click', selectChip);
  chip.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectChip(); }
  });
});

const slider = document.getElementById('chaos');
const sliderValEl = document.getElementById('chaos-val');
function updateSlider() {
  const pct = Math.round((slider.value - 1) / 9 * 100);
  slider.style.setProperty('--pct', pct + '%');
  sliderValEl.textContent = slider.value;
}
slider.addEventListener('input', updateSlider);
updateSlider();

function getSelectVal(selectId, customFieldId) {
  const sel = document.getElementById(selectId);
  if (sel.value === 'custom') return document.getElementById(customFieldId)?.value?.trim() || 'a custom setting';
  return sel.value;
}

// ── Image generation ─────────────────────────────────────────────

async function generateImages() {
  const p1 = document.getElementById('prompt-copy-1')?.value;
  const p2 = document.getElementById('prompt-copy-2')?.value;
  if (!p1 && !p2) { alert('Forge a palace first to generate image prompts.'); return; }
  if (!backendState.checked) await refreshBackendStatus();
  if (!backendState.reachable) {
    openConnectionModal();
    return;
  }
  if (!backendState.providerAuthReady) {
    openConnectionModal();
    return;
  }
  if (!backendState.geminiConfigured) {
    openConnectionModal();
    syncConnectionModal('Backend reachable, but GEMINI_API_KEY is not configured on the server yet.');
    return;
  }

  const btn = document.getElementById('generate-images-btn');
  const status = document.getElementById('gen-img-status');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span> Generating…';
  status.textContent = 'Sending prompts to Gemini…';

  document.getElementById('gen-img-1').style.display = 'none';
  document.getElementById('gen-img-2').style.display = 'none';

  const prompts = [p1, p2].filter(Boolean);
  const headers = { 'Content-Type': 'application/json' };
  if (authState.session?.access_token) {
    headers.Authorization = `Bearer ${authState.session.access_token}`;
  }

  try {
    const res = await fetch(getApiUrl('/api/generate-image'), {
      method: 'POST',
      headers,
      body: JSON.stringify({ prompts })
    });

    if (res.status === 401) {
      openAuthModal();
      throw new Error('Sign in to generate images.');
    } else if (res.status === 402) {
      const quota = await res.json().catch(() => ({}));
      throw new Error(`Monthly quota exceeded (${quota.usage?.used ?? '?'}/${quota.usage?.limit ?? '?'}).`);
    } else if (res.status === 503) {
      throw new Error('GEMINI_API_KEY is not configured on the backend.');
    } else if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || `Image generation failed (HTTP ${res.status}).`);
    }

    const data = await res.json();
    const images = data.images || [];

    images.forEach((img, i) => {
      const n = i + 1;
      const container = document.getElementById(`gen-img-${n}`);
      const el = document.getElementById(`gen-img-${n}-el`);
      if (container && el) {
        el.src = `data:${img.mime_type};base64,${img.data}`;
        container.style.display = 'block';
      }
    });

    status.textContent = `✓ ${images.length} image${images.length !== 1 ? 's' : ''} generated`;
    status.style.color = 'var(--green)';
  } catch (err) {
    status.textContent = `✗ ${err.message}`;
    status.style.color = '#f56565';
    console.error('Image generation error:', err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '✦ Generate Images';
  }
}

function downloadGenImage(n) {
  const el = document.getElementById(`gen-img-${n}-el`);
  if (!el || !el.src) return;
  const a = document.createElement('a');
  a.href = el.src;
  const topic = document.getElementById('topic')?.value?.trim() || 'palace';
  const safeName = topic.replace(/[^a-zA-Z0-9]+/g, '_').substring(0, 40);
  a.download = `${safeName}_image_${n}.png`;
  a.click();
}

// ── Main pipeline ────────────────────────────────────────────────

async function runPipeline() {
  const topic    = document.getElementById('topic').value.trim();
  const chaos    = parseInt(slider.value);
  const artStyle = document.getElementById('style-select').value;
  const tone     = document.querySelector('#tone-chips .chip.active')?.dataset.val || 'visceral and cinematic';

  if (!topic) { alert('Please describe what needs to be memorized (Section I).'); return; }

  currentStoryData = null;
  currentPromptData = { prompt1: '', prompt2: '' };
  currentQualityGateData = null;
  refreshAuthUI();

  const btn = document.getElementById('forge-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span> MNEMORIZING…';

  document.getElementById('pipeline').classList.add('visible');
  setStatus('story', 'Waiting…', '');
  setStatus('quality', 'Waiting…', '');
  setStatus('prompt', 'Waiting…', '');

  // ══ DEMO MODE — full UI flow, zero API calls ══════════════════
  if (isDemoMode()) {
    const D = DEMO_DATA;

    setStatus('story', '✦ Writing scene…', 'running');
    await demoDelay(1800);

    showBody('story');
    document.getElementById('story-header').innerHTML =
      `<div class="story-scene-title">${escapeHtml(D.scene_title)}</div>
       <div class="story-opening">${escapeHtml(D.opening)}</div>`;

    document.getElementById('vo-body').innerHTML = D.voLines.map(v => `
      <tr>
        <td><span class="row-num">${v.n}</span>${formatNarrationHtml(v.narration)}</td>
        <td>${escapeHtml(v.visual)}</td>
        <td class="encodes-cell">${escapeHtml(v.anchor)}</td>
      </tr>`).join('');
    document.getElementById('vo-table-wrap').style.display = 'block';

    document.getElementById('review-text').innerHTML = formatReviewBullets(D.review_script);
    document.getElementById('review-wrap').removeAttribute('open');
    document.getElementById('review-wrap').style.display = 'block';

    setStatus('story', '✓ Complete', 'done');
    await demoDelay(800);
    setStatus('quality', 'Demo skipped', 'done');
    renderQualityGateMessage('Demo mode uses built-in sample content, so private medical retrieval is skipped.', 'success');
    await demoDelay(400);

    setStatus('prompt', '✦ Building image prompts…', 'running');
    await demoDelay(1200);

    const n = D.voLines.length;
    const assigned = D.voLines.map((v, i) => ({ ...v, zone: ZONE_CYCLE[i % ZONE_CYCLE.length] }));

    const demoP1 = SKETCHY_STYLE + '\n\n' + D.prompt1_sample + ', aspect ratio 16:9, flat 2D cartoon';

    const demoP2 = SKETCHY_STYLE + '\n\n' + D.prompt1_sample +
      ', aspect ratio 16:9, flat 2D cartoon. \n\n' +
      `${ANTI_META_TEXT}\n\n` +
      `Add ALL ${n} of the following anchor elements to the scene in a single pass. ` +
      `Place each one in its general area using the exact visual description given — ` +
      `do not rephrase or alter the descriptions. Zone hints in parentheses are composition guidance only — do NOT render them as text:\n\n` +
      buildAnchorLines(assigned) + '\n\n' +
      `All ${n} anchors must be present and clearly identifiable in the final image. ` +
      `Text on objects must be legible. Keep all text labels SHORT — maximum 3-4 words per label to minimize spelling errors. Use numbers and abbreviations where possible instead of full words. ` +
      `Maintain same lighting, color palette, and atmosphere.`;

    showBody('prompt');
    if (isOperatorMode()) operatorPanel.classList.add('visible');
    document.getElementById('img-prompt-1').textContent = demoP1;
    document.getElementById('img-prompt-2').textContent = demoP2;
    document.getElementById('prompt-copy-1').value = demoP1;
    document.getElementById('prompt-copy-2').value = demoP2;
    setStatus('prompt', isOperatorMode()
      ? `✓ 2 prompts ready (${n} anchors in single pass)`
      : '✓ Image prompts ready', 'done');
    setCurrentPalaceData(
      {
        scene_title: D.scene_title,
        opening: D.opening,
        voLines: D.voLines,
        review_script: D.review_script
      },
      demoP1,
      demoP2
    );

    btn.disabled = false; btn.innerHTML = "LET'S MNEMORIZE";
    return;
  }
  // ══ END DEMO MODE ═════════════════════════════════════════════

  function extractTag(text, tag) {
    const re = new RegExp(`<${tag}>[\\s\\S]*?<\\/${tag}>`, 'i');
    const m = text.match(re);
    if (!m) return '';
    return m[0].replace(new RegExp(`^<${tag}>`, 'i'), '').replace(new RegExp(`<\\/${tag}>$`, 'i'), '').trim();
  }

  function extractAllTags(text, tag) {
    const re = new RegExp(`<${tag}>[\\s\\S]*?<\\/${tag}>`, 'gi');
    return [...text.matchAll(re)].map(m =>
      m[0].replace(new RegExp(`^<${tag}>`, 'i'), '').replace(new RegExp(`<\\/${tag}>$`, 'i'), '').trim()
    );
  }

  function showDebug(label, data) {
    const box = document.getElementById('debug-box');
    box.style.display = 'block';
    box.textContent = `── ${label} ──\n${typeof data === 'string' ? data : JSON.stringify(data, null, 2)}`;
  }

  function parseAPIResponse(raw, context) {
    showDebug(context + ' — raw API response', raw);
    if (raw.type === 'error' || raw.error) {
      const msg = raw.error?.message || raw.message || JSON.stringify(raw);
      throw new Error(`${context}: ${msg}`);
    }
    if (!raw.content || !Array.isArray(raw.content)) {
      throw new Error(`${context}: unexpected structure — ${JSON.stringify(raw).slice(0, 300)}`);
    }
    const text = raw.content[0]?.text;
    if (!text) {
      throw new Error(`${context}: empty content — stop_reason=${raw.stop_reason}`);
    }
    document.getElementById('debug-box').style.display = 'none';
    return text;
  }

  // ── STAGE 1: Clinical Context ─────────────────────
  setStatus('story', '✦ Analyzing topic…', 'running');
  let clinicalContext = '';
  try {
    const ctxRes = await claudeFetch({
        model: CLAUDE_MODEL,
        max_tokens: 1200,
        system: `You are a senior clinical educator and board exam question writer designing memory scenes. Extract the essential teaching points for a Sketchy-style mnemonic scene. Be EXHAUSTIVE — if a concept is commonly tested on USMLE, COMLEX, shelf exams, or in-training exams, it MUST be included.

COMPLETENESS CHECK: Before finalizing, verify you have not omitted any major category. For example:
- For scoring systems: every sub-item and its specific scoring range
- For interpretation algorithms: every step in the systematic approach
- For drug classes: mechanism, indications, contraindications, key side effects, monitoring
- For pathophysiology: etiology, pathogenesis, clinical features, diagnosis, management, complications
- For procedures/protocols: indications, contraindications, steps, complications, alternatives

Output ONLY these two XML tags, nothing else:

<core_concepts>The 8-12 most important, data-backed clinical facts that MUST be encoded — aim for comprehensive board-level coverage with ZERO important omissions. One per line. Include: diagnostic criteria, key thresholds/numbers, mechanism, first-line management steps, critical safety checks, common pitfalls, and resolution/disposition criteria. EVERY specific number, threshold, dose, duration, angle, and scoring range must be EXACT per current guidelines — no approximations, no rounding, no merging different values into one. If the topic has a well-known systematic approach (e.g. EKG interpretation steps, trauma primary survey), cover EVERY step — do not skip any.</core_concepts>
<scene_logic>How to spatially arrange these concepts in a single illustrated scene — how the eye moves left-to-right and foreground-to-background. 8-10 anchors need distinct zones across left, center, right, foreground, and background areas.</scene_logic>`,
        messages: [{ role: 'user', content: `Clinical topic: ${topic}\nLearner: ED/ICU physician — needs precise, high-yield anchors.` }]
      });
    const ctxRaw = await ctxRes.json();
    const ctxTxt = ctxRaw.content?.[0]?.text || '';
    const core   = extractTag(ctxTxt, 'core_concepts');
    const logic  = extractTag(ctxTxt, 'scene_logic');
    if (core || logic) {
      clinicalContext = `CLINICAL DESIGN CONTEXT — bake these facts and spatial logic into the scene:\n\nCORE CONCEPTS:\n${core}\n\nSCENE LAYOUT:\n${logic}\n\nEvery anchor must encode a specific fact from above.`;
    }
  } catch(e) {
    console.warn('Clinical context extraction failed (non-fatal):', e.message);
  }

  // ── STAGE 2: Voiceover Script ─────────────────────
  setStatus('story', '✦ Writing scene…', 'running');

  const storySystem = `You are writing narration for a medical memory palace video in the style of Pixorize and Sketchy Medical. The scene is a single static illustration — there is no animation or movement. The narrator is an unseen voice pointing things out directly to a medical student viewer. There is NO guide character in the scene — only objects, signs, and environmental elements.

SCENE SETTING — YOU CHOOSE:
- Pick a setting that is THEMATICALLY CONNECTED to the medical topic and made of materials that render flat (wood, paper, brick, chalkboard, fabric, cork, cardboard)
- BEST settings: bars, pubs, offices, classrooms, workshops, kitchens, libraries, old shops, speakeasies, market stalls, barber shops, diners
- AVOID settings with: glass, chrome, metal, screens, modern clinical equipment, sci-fi technology, holographic displays — these fight the flat hand-drawn style
- The setting should be clever and memorable — the connection between the setting and the topic should make the student smile or remember it more easily

NARRATION RULES — follow these exactly:
1. Direct the viewer's attention to each element — use phrases like "notice", "take a look at", "you'll see", "over here", "right here"
2. Name the visual element plainly as it appears in the static image
3. Explicitly state the mnemonic link — "this is here to help you remember...", "get it? [word] for [concept]?"
4. Immediately teach the clinical fact tied to that anchor — be specific and medically accurate
5. Conversational, friendly, slightly enthusiastic tone — like a peer tutor, not a movie narrator
6. NEVER describe movement, characters doing actions dynamically, or things happening — the image is frozen
7. NEVER use cinematic or dramatic language — no "surges", "crashes", "races", "battles"
8. Short punchy sentences — written for spoken audio, natural rhythm, easy to follow

CLINICAL ACCURACY — NON-NEGOTIABLE:
- Every number, threshold, dose, duration, and scoring range MUST be correct per current guidelines
- When combining related sub-items into one anchor, preserve EVERY specific number for EACH sub-item — do not merge or average them
- Example: if arm drift is tested at 90° for 10 seconds and leg drift is tested at 30° for 5 seconds, BOTH specific angles AND durations must appear separately — do NOT say "10 seconds" for both
- When in doubt about a specific number, use the most conservative/standard value from UpToDate or major society guidelines
- Double-check: scoring ranges, time thresholds, dose units, anatomical specifics, and classification cutoffs

COMPLETENESS — NON-NEGOTIABLE:
- Before writing anchors, mentally enumerate EVERY major category, classification, or step in the topic
- If the topic is a scoring system, EVERY item must be covered (group related items but do not skip any)
- If the topic is a stepwise process (e.g. EKG interpretation, ACLS algorithm), EVERY step must appear — do not skip steps even if they seem "obvious"
- If the topic has a classification system (e.g. types of heart block), include ALL types including the most severe/dangerous one
- Common omission errors to avoid: skipping complete/3rd-degree heart block when covering AV blocks, omitting the most severe classification tier, forgetting disposition/resolution criteria, leaving out common exceptions to rules
- After writing all anchors, review them against the topic and ask: "Is there a major testable fact or category I missed?" If yes, add another anchor.

VISUAL DESCRIPTION RULES:
- MAXIMUM 20 WORDS per visual description — this is a hard limit
- Describe ONLY: the object, its key labels/text, and its general position (left, center, right, foreground, background)
- Every anchor must be a PHYSICAL object that can be drawn flat: signs, bottles, posters, dials, chalkboards, sticky notes, jars, masks, clipboards, charts
- Do NOT describe: era-specific aesthetics, materials (wood-grain, brass, neon), technology type (holographic, digital, CRT), atmospheric details, or lighting
- Do NOT use words that imply non-flat rendering: holographic, translucent, glowing, 3D, projection, transparent, neon-lit, illuminated, LED
- TEXT ON OBJECTS: Keep all labels as SHORT as possible — use abbreviations, symbols, and numbers instead of full words. Fewer characters = fewer Gemini typos. Example: "≥1mm LIMB, ≥2mm PRECORDIAL" NOT "at least one millimeter of elevation in two contiguous limb leads." Use arrows (↑↓), symbols (≥≤±), and standard medical abbreviations aggressively.
- Good example: "A poster on the left wall showing 'QTc >440♂ >460♀ >500=TORSADES' with a formula"
- Bad example: "A 1980s neon-lit holographic display panel with brushed aluminum frame showing translucent 3D drug molecules floating in a blue glow"

ABSURDITY LEVEL: ${chaos}/10 — dial how strange the visual anchors are, not how dramatic the narration is.

${clinicalContext}

Respond using ONLY these XML tags in order. Write freely inside — no JSON:

<scene_title>Short evocative title for the memory scene</scene_title>

<opening>2-3 sentences introducing the scene. Set the location and overall vibe conversationally — like "Our scene today takes place at..." or "Welcome to...". Do not describe action or movement.</opening>

For each memory anchor output one <vo_line> block. Aim for 8-10 anchors total — cover the topic comprehensively at board-exam level, the way Sketchy Medical does. Do not stop at 5-6 if there are more high-yield facts to encode.

GROUPING RULE: If a topic has many sub-items (e.g. a scoring system with 15 items, a drug class with 12 side effects), combine closely related sub-items into a SINGLE anchor with one visual element that encodes 2-3 facts together. For example: a scoring scale's "questions" and "commands" sub-items can share one visual station; motor arm and motor leg can share one stopwatch display; language and articulation can share one communication desk. This keeps the total anchor count at 8-10 while still covering every testable fact. Each visual should encode MORE information, not less — denser per anchor, fewer total anchors.

CRITICAL: When grouping sub-items, do NOT lose specificity. If two sub-items have DIFFERENT numbers (different scoring ranges, different time limits, different angles, different doses), the visual description and narration must clearly show BOTH distinct values. For instance, if arms are tested for 10 seconds and legs for 5 seconds, the visual must show "10 SEC" AND "5 SEC" as separate labels — never collapse them into one number.
<vo_line>
NARRATION: [2-4 sentences. Direct viewer attention → name the element → state the mnemonic link explicitly → teach the clinical fact → optional reinforcement "get it? X for Y?". Natural spoken rhythm. No dramatic language. No movement descriptions.]
VISUAL: [MAXIMUM 20 WORDS. Physical object + labels + position only. No era styling, no material descriptions, no technology type, no lighting effects.]
ANCHOR: [The specific clinical fact this visual encodes — one crisp line]
</vo_line>

<review_script>
Rapid-fire recall. One line per anchor. Format: "When you see [image element] — remember [clinical fact]"
</review_script>`;

  const storyUser = `Create a Pixorize/Sketchy-style memory palace narration script for: ${topic}
Tone: ${tone}
Absurdity: ${chaos}/10
TARGET: 8-10 anchors covering this topic comprehensively at board-exam level. Do NOT omit any major category, step, or classification tier.

SETTING SELECTION (you choose): Pick a setting with a clever thematic pun or connection to the medical topic that makes it memorable. The setting MUST be made of physical, hand-drawable materials (wood, brick, paper, chalkboard, fabric, stone, ceramic) — NOT modern clinical spaces with glass, chrome, screens, or technology. Good examples: a speakeasy bar for pharmacology, a vintage workshop for procedures, a kitchen for metabolic topics, a courtroom for diagnostic criteria, a train station for stepwise algorithms, a barbershop for dermatology, a butcher shop for anatomy. The more absurd and memorable the thematic connection, the better.

NO guide character — the scene communicates entirely through objects, signs, posters, and environmental details. No people in the scene. The narrator is an unseen voice.

The narrator points out elements in a STATIC IMAGE. No movement. No action. Direct the viewer's attention to each visual anchor, state the mnemonic link explicitly, then teach the clinical fact.`;

  let storyData = null;
  let imagePromptText = '';

  try {
    const requestBody = {
      model: CLAUDE_MODEL,
      max_tokens: 4096,
      system: storySystem,
      messages: [{ role: 'user', content: storyUser }]
    };

    showDebug('STORY REQUEST (sending...)', JSON.stringify({
      model: requestBody.model,
      max_tokens: requestBody.max_tokens,
      system_length: requestBody.system.length,
      user_length: storyUser.length
    }));

    let res;
    try {
      res = await claudeFetch(requestBody);
    } catch(fetchErr) {
      throw new Error(fetchErr.message || 'Could not reach the provider proxy.');
    }

    const rawText = await res.text().catch(() => '(could not read body)');
    showDebug(`STORY RESPONSE — HTTP ${res.status}`, rawText.slice(0, 2000));

    if (!res.ok) {
      throw new Error(`Scene Narrative: HTTP ${res.status} — ${rawText.slice(0, 500)}`);
    }

    let raw;
    try {
      raw = JSON.parse(rawText);
    } catch(jsonErr) {
      throw new Error(`JSON parse failed: ${jsonErr.message} — raw: ${rawText.slice(0, 300)}`);
    }

    const txt = parseAPIResponse(raw, 'Scene Narrative');

    const scene_title   = extractTag(txt, 'scene_title');
    const opening       = extractTag(txt, 'opening');
    const review_script = extractTag(txt, 'review_script');

    const voRaw = extractAllTags(txt, 'vo_line');

    const voLines = voRaw.map((block, i) => {
      const getField = (label) => {
        const re = new RegExp(
          `${label}:\\s*\\[?([\\s\\S]*?)\\]?(?=\\n(?:NARRATION|VISUAL|ANCHOR):|$)`,
          'i'
        );
        const m = block.match(re);
        if (!m) return '';
        return m[1].replace(/\]?\s*$/, '').trim();
      };
      return {
        n:         i + 1,
        narration: getField('NARRATION'),
        visual:    getField('VISUAL'),
        anchor:    getField('ANCHOR'),
      };
    });

    storyData = { scene_title, opening, voLines, review_script };

    showBody('story');

    if (voLines.length === 0) {
      showDebug('PARSE WARNING — vo_line blocks: 0. Full raw response (first 1200 chars):', txt.slice(0, 1200));
    }

    renderStoryData(storyData);

    setStatus('story', '✓ Complete', 'done');
    await runMedicalQualityGate(storyData);
  } catch(e) {
    const box = document.getElementById('debug-box');
    const prev = box.textContent;
    box.style.display = 'block';
    box.textContent = `── STORY ERROR ──\n${e.message}\n\n── Previous debug output ──\n${prev}`;
    setStatus('story', '✗ ' + e.message.slice(0, 80), 'error');
    btn.disabled = false; btn.innerHTML = "LET'S MNEMORIZE";
    return;
  }

  // ── STAGE 3: Image prompts ────────────────────────
  setStatus('prompt', '✦ Building image prompts…', 'running');

  try {
    const n = storyData.voLines.length;
    const assigned = storyData.voLines.map((v, i) => ({
      ...v,
      zone: ZONE_CYCLE[i % ZONE_CYCLE.length]
    }));

    const ipSystem = 'You write scene descriptions for Gemini Imagen image generation. ' +
      'Output ONLY the scene-specific content — setting, objects, composition, atmosphere. ' +
      'Dense, comma-separated descriptive phrases. Do NOT include any style instructions, art style language, ' +
      'or rendering directives — those are handled separately. ' +
      'YOUR MOST IMPORTANT JOB: Choose a setting/location that is thematically clever for the medical topic ' +
      'AND renders well as a flat hand-drawn illustration. Best settings use physical materials: ' +
      'wood, paper, brick, chalkboard, cork, fabric, stone, ceramic. ' +
      'Examples of GOOD settings: a speakeasy bar (for pharmacology), a cluttered professors office (for scoring systems), ' +
      'a vintage workshop (for procedural topics), a kitchen (for metabolic topics), a train station (for algorithms). ' +
      'Examples of BAD settings: research facilities, hospitals, modern labs, anything with glass/chrome/screens/technology. ' +
      'The setting should have a memorable thematic connection to the topic that makes it stick in memory.';

    const p1UserMsg = `Write a scene description for a memory palace illustration. Output ONLY the scene content — no style directives.

MEDICAL TOPIC: ${topic}
SCENE TITLE: ${storyData.scene_title}
ATMOSPHERE: ${storyData.opening}
TOTAL ANCHORS TO FIT: ${n} (scene must be wide and spacious enough)

Requirements:
- 60-80 words maximum — scene content ONLY, no style language
- Choose a setting that has a clever thematic connection to the medical topic — make it memorable and slightly absurd
- The setting MUST be made of flat-friendly materials: wood, paper, brick, chalkboard, cork, cardboard, fabric, stone, ceramic — ABSOLUTELY NO glass, chrome, metal panels, screens, monitors, or modern clinical equipment
- NO guide character — the scene is empty of people, only objects and environment
- Scene wide enough to hold ${n} distinct objects spread across left, center, right, foreground, and background
- End with: wide establishing shot, enough space for ${n} labeled objects, aspect ratio 16:9`;

    const p1Res = await claudeFetch({
        model: CLAUDE_MODEL,
        max_tokens: 300,
        system: ipSystem,
        messages: [{ role: 'user', content: p1UserMsg }]
      });
    if (!p1Res.ok) throw new Error(`Image Prompt 1: HTTP ${p1Res.status} — ${await p1Res.text()}`);
    const p1Raw = await p1Res.json();
    const sceneDesc = parseAPIResponse(p1Raw, 'Scene Description').trim();

    const prompt1 = SKETCHY_STYLE + '\n\n' + sceneDesc + ', aspect ratio 16:9, flat 2D cartoon';

    const prompt2 = SKETCHY_STYLE + '\n\n' + sceneDesc +
      ', aspect ratio 16:9, flat 2D cartoon. \n\n' +
      `${ANTI_META_TEXT}\n\n` +
      `Add ALL ${n} of the following anchor elements to the scene in a single pass. ` +
      `Place each one in its general area using the exact visual description given — ` +
      `do not rephrase or alter the descriptions. Zone hints in parentheses are composition guidance only — do NOT render them as text:\n\n` +
      buildAnchorLines(assigned) + '\n\n' +
      `All ${n} anchors must be present and clearly identifiable in the final image. ` +
      `Text on objects must be legible. Keep all text labels SHORT — maximum 3-4 words per label to minimize spelling errors. Use numbers and abbreviations where possible instead of full words. ` +
      `Maintain same lighting, color palette, and atmosphere.`;

    showBody('prompt');
    if (isOperatorMode()) operatorPanel.classList.add('visible');
    document.getElementById('img-prompt-1').textContent = prompt1;
    document.getElementById('img-prompt-2').textContent = prompt2;
    document.getElementById('prompt-copy-1').value = prompt1;
    document.getElementById('prompt-copy-2').value = prompt2;

    setStatus('prompt', '✦ Image prompts ready', 'done');
    setCurrentPalaceData(storyData, prompt1, prompt2);

  } catch(e) {
    setStatus('prompt', `✦ PROMPT ERROR ── ${e.message}`, 'error');
    console.error('Image prompt error:', e);
    setCurrentPalaceData(storyData, '', '');
  }

  btn.disabled = false;
  btn.innerHTML = '✦ FORGE PALACE';
}

// ── PWA service worker registration ──────────────────────────────

if ('serviceWorker' in navigator && window.location.protocol !== 'file:') {
  navigator.serviceWorker
    .register('/sw.js', { updateViaCache: 'none' })
    .then(registration => registration.update())
    .catch(() => {});
}
