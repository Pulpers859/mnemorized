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
  'Rich saturated color palette — use vivid Copic marker colors (teal, amber, crimson, forest green, ' +
  'warm orange, dusty blue, plum) with strong contrast against a clean cream or white background. ' +
  'Characters are angular cartoon caricatures with big heads, pointy chins, exaggerated expressions — ' +
  'like editorial newspaper cartoons, NOT anime, NOT 3D, NOT realistic proportions. ' +
  'Backgrounds filled with hand-drawn linework and flat marker fills — clean, not heavily cross-hatched. ' +
  'NO gradient fills, NO atmospheric haze, NO depth of field blur, NO film grain, NO paper texture noise. ' +
  'Flat even lighting — NO spotlight cones, NO volumetric light, NO lens flares, NO glowing effects. ' +
  'All text in the scene looks hand-written with a marker, slightly uneven and imperfect. ' +
  'Every object looks like it was drawn on a whiteboard or poster board with markers. ' +
  'Style principles: hand-drawn educational visual mnemonic poster, editorial cartoon caricature, dense but readable medical teaching map.';

const SKETCHY_STYLE_ROOM = 'Hand-drawn 2D cartoon illustration drawn with Micron pens and Copic markers on paper then scanned. ' +
  'Wobbly, imperfect ink outlines with visible line weight variation — thick at corners, thin on straights, ' +
  'slightly unsteady like a real human hand drew every line. NO clean digital vector lines. ' +
  'Cell-shaded flat coloring: each surface has ONE base color and ONE shadow color with a HARD crisp edge, ' +
  'like coloring with markers that leave visible fill strokes. NO soft gradients, NO airbrush, NO blending. ' +
  'Rich saturated color palette — use vivid Copic marker colors (teal, amber, crimson, forest green, ' +
  'warm orange, dusty blue, plum) with strong contrast against a clean cream or white background. ' +
  'Backgrounds filled with hand-drawn linework and flat marker fills — clean, not heavily cross-hatched. ' +
  'NO gradient fills, NO atmospheric haze, NO depth of field blur, NO film grain, NO paper texture noise. ' +
  'Flat even lighting — NO spotlight cones, NO volumetric light, NO lens flares, NO glowing effects. ' +
  'Every object looks like it was drawn on a whiteboard or poster board with markers. ' +
  'Style principles: hand-drawn educational visual mnemonic poster, editorial cartoon background, dense but readable medical teaching map. ' +
  'EMPTY ROOM ONLY — absolutely NO people, NO characters, NO figures, NO animals. ' +
  'NO text, NO labels, NO signs, NO writing on any surface. Just the bare room.';

// Positive framing, not negation: image models cannot parse "do NOT" — each negated
// noun CUES the thing it forbids. State the desired POSITIVE surface state instead, and
// require every label to sit physically ON its own object (Constitution LAW 2; real-pixel
// validated 2026-07-09, floating labels 7 -> 0 when this framing replaced the negation).
const ANTI_META_TEXT = 'TEXT RULES: Every wall, the floor, the ceiling, and all empty space are completely ' +
  'blank and unmarked. The only writing anywhere is short words physically lettered ON the in-world object ' +
  'each one belongs to — printed on the object itself, a sign, a bottle, a banner, or a chalkboard, and ' +
  'sitting directly on that object. Nothing is written in the empty air or space around the objects.';

const NO_PRECISION_TEXT_RULE = 'NO PRECISION TEXT: do NOT render numbers, digits, doses, units, thresholds, lab values, percentages, or formulas as written text anywhere in the image — no plaques, dials, gauges, tags, chalk marks, or stamps bearing values. ' +
  'A drawn number is a flashcard, not a mnemonic: the exact value is spoken in the narration and listed in the flashcards, NOT printed in the picture. ' +
  'A number may appear ONLY when it is ENCODED as a visual hook — a shape look-alike (a fork\'s 3 prongs = a triad) or a small countable quantity of oversized objects (at most ~5) — never as spelled-out digits on a surface. ' +
  'If a value cannot be cleanly encoded as a hook, leave it OUT of the image entirely; the narration carries it.';

const ANCHOR_LEGIBILITY_RULE = 'ANCHOR LEGIBILITY RULE: every anchor must be large enough to identify at normal 1024px image size. ' +
  'No anchor may become tiny shelf clutter. Give each anchor clear empty space, a distinct silhouette, and enough scale to read its key shape before reading any label. ' +
  'If a shelf or wall contains multiple anchors, stagger them vertically and enlarge each one instead of lining up small similar props.';

const EXACT_LABEL_RULE = 'EXACT LABEL RULE: if a visual specifies a short label, copy it exactly. ' +
  'Do not invent alternate spellings, abbreviations, or nonsense words. Sound-alike character names must appear exactly when the name carries the mnemonic. ' +
  'If exact text would be too small or uncertain, replace it with a larger physical symbol instead of misspelling it.';

// Sanctioned universal metaphor catalog — Mnemorized's OWN approved, common-knowledge
// vocabulary (NOT proprietary). Mirrors docs/visual-metaphor-library.txt — keep the two in
// sync. Injected into the Stage-2 story prompt so the model reaches for a pure visual
// metaphor (tier 1) instead of collapsing to a text-labeled generic prop.
const VISUAL_METAPHOR_LIBRARY = [
  'Electrolytes/chemistry: banana bunch = potassium (K+); salt sack/shaker or salt crystals = sodium (Na+) / normal saline; lemon or acid-green liquid = acidosis / low pH; golden honey or sugar cubes = glucose / hyperglycemia; purple flame = ketones; bone or milk carton = calcium; horseshoe magnet = magnesium; a box of baking soda (household carton) = bicarbonate (NaHCO3); water/rain = hydration/fluids; red blood drop = hemoglobin.',
  'Speed/timing: turtle or snail = slow/careful correction; rabbit = fast/urgent; hourglass or clock face = time window; stopwatch = specific time threshold; metronome = rate/rhythm.',
  'Danger/restriction: skull & crossbones = death/toxicity; red X = contraindicated; padlock = restricted / hold / locked away; brick wall or sealed door = completely blocked / never; warning triangle = caution; alarm bell = emergency; cracked/shattered object = organ damage.',
  'Treatment actions: fire hose/flood = aggressive fluid resuscitation; barely-open valve = low-dose infusion; syringe pinching skin = subcutaneous; IV bag dripping = intravenous; chisel chipping = steady anticoagulation; dynamite = thrombolysis; shield = prophylaxis; sword = first-line; bow & arrow = second-line; lever/control panel = refractory/escalation.',
  'Monitoring/diagnosis: balance scale = risk scoring; magnifying glass = diagnostic test; waveform monitor = continuous monitoring; needle gauge = a vital/lab value; clipboard with checkmarks = scoring checklist; dipstick = point-of-care test.',
  'Anatomy/pathology: swollen/cracked object = edema; bulging cracked wall = chamber dilation/strain; dark clot mass = thrombus/embolism; blocked pipe = vascular occlusion; iron grate = filter (e.g. IVC filter); closing gap in the floor = anion gap; overflowing container = excess/uncontrolled level.',
  'Temperature: ice/frost = hypothermia/cooling; fire/flames = fever/inflammation; steam = warming.',
  'Body systems (setting-level): bellows = lungs; pump/engine = heart; pipes/plumbing = vasculature; wires = nervous conduction; sieve/filter = kidney; factory/refinery = metabolism; clock tower with gears = brain (sparking gears = seizure).',
  'RULES: one metaphor per concept globally (never reuse a metaphor for a different meaning); oversize the metaphor object so it dominates its zone; if a pure metaphor could be ambiguous, add ONE short hybrid label ON the object rather than dropping to a bare label.',
].map(function (line) { return '- ' + line; }).join('\n');

const ZONE_CYCLE = [
  'FAR LEFT', 'LEFT', 'CENTER LEFT', 'CENTER', 'CENTER RIGHT', 'RIGHT',
  'FAR RIGHT', 'FOREGROUND LEFT', 'FOREGROUND CENTER', 'FOREGROUND RIGHT',
  'BACKGROUND LEFT', 'BACKGROUND CENTER', 'BACKGROUND RIGHT', 'BACKGROUND CORNER', 'DOORWAY'
];

const ZONE_KEYWORDS = [
  [/\b(?:far\s+)?left\s+wall\b/i, 'LEFT WALL'],
  [/\b(?:far\s+)?right\s+wall\b/i, 'RIGHT WALL'],
  [/\bback\s+(?:corner|wall)\b/i, 'BACKGROUND CORNER'],
  [/\bforeground\b/i, 'FOREGROUND CENTER'],
  [/\bcenter\b/i, 'CENTER'],
  [/\bceiling\b/i, 'ABOVE CENTER'],
  [/\bfloor\b|on\s+the\s+ground\b/i, 'FOREGROUND CENTER'],
  [/\bleft\b/i, 'LEFT'],
  [/\bright\b/i, 'RIGHT'],
];

const IMAGE_PROMPT_MAX_CHARS = 7800;

function extractZone(visual, fallback) {
  for (const [re, zone] of ZONE_KEYWORDS) {
    if (re.test(visual)) return zone;
  }
  return fallback;
}

function assignZones(voLines) {
  return voLines.map((v, i) => ({
    ...v,
    zone: extractZone(v.visual, ZONE_CYCLE[i % ZONE_CYCLE.length])
  }));
}

function condenseForImage(visual) {
  let s = visual;
  s = s.replace(/[↑↓]/g, '');
  s = s.replace(/(^|[\s(:])"([^"]{25,})"/g, (_, prefix, inner) => {
    if (/[=×+\-±<>≤≥÷/]|(?:\d)/.test(inner) && inner.length <= 70) return prefix + '"' + inner + '"';
    const parts = inner.split(/[\/,;]+/).map(p => p.trim()).filter(Boolean);
    if (parts.length > 2) return prefix + '"' + parts.slice(0, 2).join(' / ') + ' …"';
    return prefix + '"' + inner.substring(0, 24) + '…"';
  });
  s = s.replace(/\s*(?:with checklist|with tags|stamped|carved|labeled)[:\s]+("[^"]*"(?:\s*(?:and|,)\s*"[^"]*")*)/gi,
    (match) => match.length > 60 ? match.substring(0, 55) + '…' : match);
  return s;
}

function trimWords(text, maxWords) {
  const words = String(text || '').trim().split(/\s+/).filter(Boolean);
  if (words.length <= maxWords) return words.join(' ');
  return words.slice(0, maxWords).join(' ') + '...';
}

// Emit UNNUMBERED, visual-only anchor lines. We deliberately drop the "Anchor N:"
// index, the "Hook:" cue, and the "Encodes:" medical prose:
//  - "Anchor N:" numbering leaks into the render as floating digit captions
//    (Constitution field finding #7 — capped plate_2 iter1/iter2 at 85 via gate G3).
//  - "Encodes:" is paragraph-length medical prose the image model must never render.
// The tested precision numbers/formulas survive inside `visual` as quoted tokens,
// which the closing allowlist fence (buildTextAllowlistFence) whitelists explicitly.
// Per-anchor word budget. The old 32-word cap silently truncated rich anchors
// mid-clause, dropping trailing sub-cues (e.g. one of a 5-part toxidrome) AND the
// quoted precision labels the closing fence still demanded — so the model rendered
// those labels blind and garbled them, and dropped "no text here" guidance. A
// generous cap (with clampImagePrompt as the hard char backstop and the concise
// fallback for overflow) keeps a multi-part anchor and its labels intact.
// Defense-in-depth for the NO-PRECISION-TEXT rule: even if an anchor visual (legacy
// script, or a non-compliant upstream) still spells a number/dose/formula as a quoted
// label to render, strip it from the drawn prompt so the model is never TOLD to draw a
// value. Only quoted PRECISION tokens are removed (and a dangling "reads/labeled" verb);
// quoted NAMES ("Pred") and unquoted shape hooks ("three prongs", "figure-8") are kept.
function stripPrecisionTokens(text) {
  const isPrecision = (t) =>
    /[0-9=×+\-±<>≤≥÷%]|\b(?:mL|kg|mg|mcg|mmol|mEq|mOsm|bpm|hr|min|U\/)\b/i.test(t);
  return String(text || '')
    .replace(/\b(?:reads?|reading|labell?ed|marked|stamped|shows?|says?|displays?|engraved|etched|inscribed|printed)\s+["“”]([^"“”\n]{1,40})["“”]/gi,
      (m, tok) => (isPrecision(tok) ? '' : m))
    .replace(/["“”]([^"“”\n]{1,40})["“”]/g, (m, tok) => (isPrecision(tok) ? '' : m))
    .replace(/\s{2,}/g, ' ').replace(/\s+([.,;])/g, '$1').trim();
}

// Zone -> natural prose lead-in phrase, so placement still guides the composition WITHOUT
// emitting an annotated "(zone)" tag. An image model imitates prompt STRUCTURE: a tagged
// list renders as a labeled DIAGRAM with floating captions; continuous scene prose renders
// as a SCENE (Constitution LAW 1). The parenthetical zone tag was itself a top cause of the
// floating-label failure (real-pixel validated 2026-07-09).
const ZONE_LEAD_IN = {
  'far left': 'On the far left', 'left': 'On the left', 'left wall': 'Against the left wall',
  'center left': 'Just left of center', 'center': 'At center stage', 'center right': 'Just right of center',
  'right': 'On the right', 'right wall': 'Against the right wall', 'far right': 'On the far right',
  'foreground left': 'In the foreground at left', 'foreground center': 'In the foreground',
  'foreground right': 'In the foreground at right', 'background left': 'In the back at left',
  'background center': 'In the background', 'background right': 'In the back at right',
  'background corner': 'Off in the back corner', 'above center': 'Directly overhead', 'doorway': 'In the doorway'
};

function zoneLeadIn(zone) {
  const z = String(zone || '').trim().toLowerCase();
  return ZONE_LEAD_IN[z] || (z ? ('Toward the ' + z) : '');
}

// Compose the anchors as ONE flowing paragraph of scene prose, never an annotated list.
// Placement rides in a natural lead-in phrase; if the visual already opens with its own
// placement word, the lead-in is skipped to avoid double-placement.
function buildImageAnchorLines(anchors, concise = false) {
  return anchors.map(v => {
    const visual = trimWords(stripPrecisionTokens(condenseForImage(v.visual)), concise ? 24 : 48)
      .replace(/[.\s]+$/, '').trim();
    if (!visual) return '';
    const lead = zoneLeadIn(v.zone);
    const alreadyPlaced = /^(on |at |in |against |just |directly |off |toward |above |below |behind |beside |near |far |left|right|center|foreground|background|upstage|downstage|stage-)/i.test(visual);
    if (lead && !alreadyPlaced) {
      return `${lead}, ${visual.charAt(0).toLowerCase()}${visual.slice(1)}.`;
    }
    return `${visual}.`;
  }).filter(Boolean).join(' ');
}

// Deterministically split the anchor visuals' "quoted" tokens into precision
// (numbers/doses/units/formulas) vs ordinary (short mnemonic names/words). Precision
// tokens are NOT renderable text — a drawn number is a flashcard, not a mnemonic, so
// exact values live in the narration + flashcards, never in the picture. Only the
// ordinary short names are allowed to appear; the precision list is returned solely so
// the fence can explicitly forbid those exact strings. Nothing is guessed.
function extractRenderableLabels(anchors) {
  const precision = [];
  const ordinary = [];
  const seen = new Set();
  const isPrecision = (t) =>
    /[0-9=×+\-±<>≤≥÷%]|\b(?:mL|kg|mg|mcg|mmol|mEq|mOsm|bpm|hr|min|U\/)\b/i.test(t);
  (anchors || []).forEach(v => {
    const src = String(v.visual || '');
    const re = /["“”]([^"“”\n]{1,40})["“”]/g;
    let m;
    while ((m = re.exec(src)) !== null) {
      const tok = m[1].trim();
      if (!tok) continue;
      const key = tok.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      (isPrecision(tok) ? precision : ordinary).push(tok);
    }
  });
  // Ordinary short names only are renderable; precision is surfaced for the ban list.
  return { precision: precision.slice(0, 6), ordinary: ordinary.slice(0, 12) };
}

// Build the closing hard-whitelist fence: the exact list of renderable text plus
// an explicit ban on index numbers / list digits (the leak class from finding #7)
// and any floating meta-text. This is always appended as the LITERAL LAST LINE of
// the anchor prompt, so whichever builder wrote the body, the guarantee holds.
function buildTextAllowlistFence(anchors) {
  const n = (anchors || []).length;
  const { ordinary } = extractRenderableLabels(anchors);
  const list = ordinary.length
    ? `The ONLY text allowed is this whitelist of short mnemonic names, each appearing at most once, ` +
      `rendered legibly on its own object: ${ordinary.join(', ')}.`
    : `This scene has NO required labels — render no visible text at all.`;
  return `RENDERABLE TEXT ALLOWLIST — treat this as a hard whitelist. ` +
    `Every wall, the floor, the ceiling, the beams, and all empty space stay completely blank and unmarked, and each allowed word sits directly on its own object. ${list} ` +
    `Do NOT render any numbers, digits, doses, units, thresholds, lab values, percentages, or formulas as text anywhere in the image — ` +
    `those exact facts belong in the narration and flashcards, not the picture. ` +
    `Do NOT render any index numbers, list numbers, bullet numbers, or the digits 1 through ${n || 10} ` +
    `as captions, tags, or labels anywhere in the image. ` +
    `No other text, no floating captions, no zone labels, no anchor descriptions, ` +
    `no speech bubbles, no directional words, no title, and no legend anywhere in the image.`;
}

// Guarantee the deterministic fence is the last thing in a prompt no matter which
// builder authored the body (local composer, Claude fallback, or the server-side
// Gemini prompt director). Idempotent: a body that already carries our fence marker
// is returned unchanged so no path double-fences.
function ensureTextAllowlistFence(prompt, anchors) {
  const text = String(prompt || '');
  if (text.includes('RENDERABLE TEXT ALLOWLIST')) return text;
  return text.replace(/\s+$/, '') + '\n\n' + buildTextAllowlistFence(anchors);
}

function composeImagePrompt2(sceneDesc, assigned, concise = false) {
  const n = assigned.length;
  return SKETCHY_STYLE + '\n\n' + trimWords(sceneDesc, concise ? 45 : 70) +
    ', aspect ratio 16:9, flat 2D cartoon.\n\n' +
    `${ANTI_META_TEXT}\n\n` +
    `SCENE OBJECT RULE: Do NOT label or name any part of the room itself (walls, floor, ceiling, beams, furniture). ` +
    `Background surfaces are unlabeled.\n\n` +
    `Add ALL ${n} of the following medical mnemonic anchors to the scene. ` +
    `Anchors may be objects, characters/figures, or interactive elements — they are VISUAL MNEMONICS, not labeled props. ` +
    `Preserve clear spatial hierarchy: left/center/right/foreground/background zones must stay readable and uncluttered. ` +
    `Each anchor should be recognizable by its SHAPE and SILHOUETTE first. ` +
    `${ANCHOR_LEGIBILITY_RULE} ` +
    `Text labels are secondary and optional — if present, maximum 3 words per ordinary mnemonic name label. ` +
    `${NO_PRECISION_TEXT_RULE} ` +
    `${EXACT_LABEL_RULE} ` +
    `SCENE TEXT BUDGET: at most 12 short mnemonic name labels in the ENTIRE image, and ZERO numeric/dose/threshold/formula text. Character names count. ` +
    `Weave ALL of them into ONE flowing scene, written as continuous prose describing a single wide shot — a narrator walking the room, never a bulleted or tagged list:\n\n` +
    buildImageAnchorLines(assigned, concise) + '\n\n' +
    `All ${n} anchors must be present, visually distinct, and each rendered EXACTLY ONCE — do not duplicate, mirror, or repeat any anchor object or figure anywhere else in the scene. ` +
    `Do NOT add labels to room surfaces, walls, beams, or background objects. ` +
    `Maintain same lighting, color palette, and atmosphere.\n\n` +
    buildTextAllowlistFence(assigned);
}

function clampImagePrompt(prompt, maxChars = IMAGE_PROMPT_MAX_CHARS) {
  const text = String(prompt || '').trim();
  if (text.length <= maxChars) return text;
  return text.slice(0, maxChars - 180).replace(/\s+\S*$/, '') +
    '\n\nFINAL HARD LIMIT: preserve all anchors above; do not add extra labels or checklist text.';
}

function normalizeImagePromptPair(pair) {
  return {
    ...pair,
    prompt1: clampImagePrompt(pair.prompt1),
    prompt2: clampImagePrompt(pair.prompt2),
  };
}

function composeImagePromptPair(sceneDesc, assigned) {
  const prompt1 = SKETCHY_STYLE_ROOM + '\n\n' + trimWords(sceneDesc, 55) + ', aspect ratio 16:9, flat 2D cartoon';
  let prompt2 = composeImagePrompt2(sceneDesc, assigned, false);
  if (prompt2.length > IMAGE_PROMPT_MAX_CHARS) {
    prompt2 = composeImagePrompt2(sceneDesc, assigned, true);
  }

  return normalizeImagePromptPair({ prompt1, prompt2, scene_description: sceneDesc, director: 'local' });
}

async function buildClaudeImagePromptPair(topic, storyData, assigned, stage) {
  const n = assigned.length;
  const ipSystem = 'You write scene descriptions for Gemini image generation. ' +
    'Output ONLY the spatial layout and atmosphere — surfaces, materials, lighting, camera angle. ' +
    'Dense, comma-separated descriptive phrases. Do NOT include any style instructions or rendering directives. ' +
    'CRITICAL: Describe the ROOM/SPACE only — walls, floor, ceiling, general surfaces. ' +
    'Do NOT name or list specific objects (no "anvil in center", "tongs hanging from beam", "bellows on wall"). ' +
    'The anchor objects are added separately — your job is ONLY the empty room that they will be placed into. ' +
    'Design the room as a clear spatial memory map with open, uncluttered zones for anchors.';

  const p1UserMsg = `Write a scene description for a memory palace illustration. Output ONLY the scene/room — no objects, no style directives.

MEDICAL TOPIC: ${topic}
SCENE TITLE: ${storyData.scene_title}
ATMOSPHERE: ${storyData.opening}
TOTAL ANCHORS TO FIT: ${n}

Requirements:
- 40-60 words maximum — room/space description ONLY
- Describe ONLY: walls, floor, ceiling, doorways, windows, general surfaces and their materials
- Do NOT name any specific objects, furniture, or tools — those are added separately as medical anchors
- Flat-friendly materials: wood, paper, brick, chalkboard, cork, cardboard, fabric, stone, ceramic — NO glass, chrome, screens, or modern clinical equipment
- NO people or characters
- Wide establishing shot, spacious enough for ${n} objects in distinct uncluttered zones, aspect ratio 16:9`;

  const p1Res = await claudeFetch({
    model: CLAUDE_MODEL,
    max_tokens: 300,
    system: ipSystem,
    messages: [{ role: 'user', content: p1UserMsg }]
  }, stage);
  if (!p1Res.ok) throw new Error(`Image Prompt 1: HTTP ${p1Res.status} — ${await p1Res.text()}`);
  const p1Raw = await p1Res.json();
  const sceneDesc = parseProviderContent(p1Raw, 'Scene Description').trim();
  return composeImagePromptPair(sceneDesc, assigned);
}

function buildGeminiPromptDirectorPayload(topic, storyData, assigned, mode) {
  return {
    topic,
    scene_title: storyData.scene_title || '',
    opening: storyData.opening || '',
    mode: mode || 'initial',
    anchors: assigned.map(v => ({
      n: Number(v.n) || 1,
      hook: v.hook || '',
      visual: v.visual || '',
      anchor: v.anchor || '',
      zone: v.zone || '',
    })),
  };
}

async function buildGeminiImagePromptPair(topic, storyData, assigned, mode, stage) {
  const res = await geminiPromptDirectorFetch(
    buildGeminiPromptDirectorPayload(topic, storyData, assigned, mode),
    stage
  );
  if (!res.ok) {
    const raw = await res.text().catch(() => '');
    throw new Error(`Gemini prompt director: HTTP ${res.status} — ${raw.slice(0, 300)}`);
  }
  const data = await res.json();
  if (!data.prompt1 || !data.prompt2) {
    throw new Error('Gemini prompt director returned an incomplete prompt pair.');
  }
  return normalizeImagePromptPair({
    prompt1: data.prompt1,
    prompt2: ensureTextAllowlistFence(data.prompt2, assigned),
    scene_description: data.scene_description || '',
    director: 'gemini',
    model: data.model || 'gemini',
  });
}

function shouldFallbackFromGeminiDirector(error) {
  const message = String(error?.message || '').toLowerCase();
  return !(
    message.includes('monthly quota') ||
    message.includes('sign in') ||
    message.includes('auth') ||
    message.includes('rate limit')
  );
}

async function buildImagePromptPair(topic, storyData, mode, geminiStage, claudeStage) {
  const assigned = assignZones(storyData.voLines);
  if (!backendState.checked) await refreshBackendStatus();

  if (backendState.geminiConfigured || getReplayMode() === 'replay') {
    try {
      return await buildGeminiImagePromptPair(topic, storyData, assigned, mode, geminiStage);
    } catch (error) {
      console.warn('Gemini prompt director failed:', error.message);
      if (!shouldFallbackFromGeminiDirector(error)) throw error;
      setStageDetail('prompt', `Gemini constitution director failed; falling back to Claude room composer.`);
    }
  }

  const fallback = await buildClaudeImagePromptPair(topic, storyData, assigned, claudeStage);
  fallback.director = 'claude-fallback';
  return fallback;
}

function renderImagePromptPair(storyData, pair, doneStatus, detail) {
  showBody('prompt');
  if (isOperatorMode()) operatorPanel.classList.add('visible');
  document.getElementById('img-prompt-1').textContent = pair.prompt1;
  document.getElementById('img-prompt-2').textContent = pair.prompt2;
  document.getElementById('prompt-copy-1').value = pair.prompt1;
  document.getElementById('prompt-copy-2').value = pair.prompt2;
  setCurrentPalaceData(storyData, pair.prompt1, pair.prompt2);
  window.MnemorizedGuided?.onStoryReady?.(storyData);
  setStatus('prompt', doneStatus, 'done');
  setStageDetail('prompt', detail);
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
      hook: 'look-alike — three-pronged trident shape encodes the diagnostic triad',
      narration: 'Take a look at the trident mounted above the entrance — three prongs, each with a number etched into the metal: 250, 7.3, and 18. Three prongs, three criteria. Get it? Glucose above 250, pH below 7.3, bicarb below 18. And notice the gap in the wall right behind it — a literal gap in the brickwork. That\'s your anion gap metabolic acidosis. All three prongs plus the gap equals DKA.',
      visual: 'Trident mounted above entrance with numbers 250, 7.3, 18 on each prong, a visible gap in the brick wall behind it',
      anchor: 'DKA diagnostic triad: glucose >250 mg/dL, pH <7.3, bicarb <18 mEq/L, plus anion gap metabolic acidosis'
    },
    {
      n: 2,
      hook: 'functional — bartender pouring fluid mirrors IV fluid resuscitation, two giant glasses = 1-2L bolus',
      narration: 'Now look at the bartender — pouring from a massive jug labeled "NS" into two enormous pint glasses. The clock on the wall behind them reads "HOUR 1" and the glasses are marked "1L" each. That\'s your initial fluid resuscitation: 1 to 2 liters of normal saline bolused in the first hour. Fluids come first in DKA. Before insulin, before anything else. The body is profoundly volume depleted — sometimes 6 to 9 liters down.',
      visual: 'Bartender pouring from giant "NS" jug into two oversized 1L pint glasses, wall clock showing "HOUR 1"',
      anchor: 'Initial fluid resuscitation: 1-2L normal saline bolus in the first hour; fluids before insulin; patients are 6-9L volume depleted'
    },
    {
      n: 3,
      hook: 'contrast — full bottle vs empty bottle at a threshold line encodes the fluid switch point at glucose 200',
      narration: 'Over on the left side of the bar, notice two bottles on a shelf with a line drawn between them at "200." Above the line, a full NS bottle. Below, a bottle of D5 half-NS. This is your fluid switch point. Once glucose drops below 200, don\'t stop fluids — switch to dextrose-containing fluids. This prevents hypoglycemia while you keep the insulin drip running to close the anion gap.',
      visual: 'Two bottles on left shelf divided by a line marked "200" — NS bottle above, D5 half-NS below the threshold',
      anchor: 'Switch to D5 ½NS when glucose <200 mg/dL — continue insulin to close anion gap, add dextrose to prevent hypoglycemia'
    },
    {
      n: 4,
      hook: 'functional — slow dripping tap mirrors continuous insulin drip; a smashed shot glass = no bolus',
      narration: 'Right here behind the bar, see the beer tap dripping slowly and steadily — "0.1 u/kg/hr" engraved on the handle. And on the floor below it, a smashed shot glass with a red X painted over it. That\'s your insulin protocol: slow continuous drip only, no bolus shot. The bolus was removed from modern protocols because it increases hypoglycemia and hypokalemia risk without improving outcomes. Just the drip, never the shot.',
      visual: 'Beer tap dripping steadily with "0.1" on handle, smashed shot glass with red X on the floor below it',
      anchor: 'Insulin drip: 0.1-0.14 units/kg/hr continuous infusion; do NOT give insulin bolus — increases hypoglycemia and hypokalemia risk'
    },
    {
      n: 5,
      hook: 'contrast — traffic light color coding (red/yellow/green) encodes three potassium thresholds and actions',
      narration: 'Now this is critical — look at the three bottles on the right side of the bar, color-coded like a traffic light. The red one has a STOP hand on it — K below 3.3, hold insulin. The yellow one shows a slow-pour — K 3.3 to 5.3, add 20-40 mEq. The green one just says "recheck." If you start insulin when potassium is below 3.3, you will drive it further down and cause fatal arrhythmias. Always check potassium before starting the drip.',
      visual: 'Three traffic-light colored bottles on right shelf: red with STOP hand, yellow with slow-pour, green with checkmark',
      anchor: 'Potassium protocol: K<3.3 = hold insulin and replete aggressively; K 3.3-5.3 = add 20-40 mEq/L to IVF; K>5.3 = recheck in 2 hours'
    },
    {
      n: 6,
      hook: 'functional — "CLOSING TIME" sign = resolution criteria; crossed-out glucose meter = follow the gap not glucose',
      narration: 'Notice the chalkboard behind the bartender. At the top it says "CLOSING TIME" and underneath there\'s a hand-drawn gap in the board narrowing to a close — the anion gap closing. A glucose meter is crossed out with a big X. This is how you know DKA is resolving. You follow the gap, not glucose. Resolution means: gap closed, pH above 7.3, bicarb above 18, and the patient can eat. Then overlap subcutaneous insulin 2 hours before stopping the drip.',
      visual: 'Chalkboard reading "CLOSING TIME" with a drawn gap narrowing shut, a crossed-out glucose meter beside it',
      anchor: 'Monitor anion gap (not glucose) for DKA resolution; resolution = gap closed + pH>7.3 + bicarb>18 + tolerating PO; overlap SQ insulin 2hr before stopping drip'
    },
    {
      n: 7,
      hook: 'sound-alike — jukebox with 5 song slots, each "I" title sounds like the precipitant',
      narration: 'Look at the jukebox in the far left corner. Five song slots, each starting with "I" — Infection, Insulin noncompliance, Ischemia, Intoxication, and Iatrogenic. The top slot is lit up brightest because infection is the number one cause. Get it? Five I\'s on the jukebox, five precipitants of DKA. Every DKA workup should include a search for the trigger.',
      visual: 'Retro jukebox in far left corner with 5 glowing song slots, top slot brightest, all titles start with "I"',
      anchor: 'DKA precipitants (5 I\'s): Infection (#1 cause), Insulin noncompliance (#2), Ischemia, Intoxication, Iatrogenic'
    },
    {
      n: 8,
      hook: 'spatial — bathroom door blocked by a bouncer encodes "do not give bicarb"; the 6.9 on the bouncer\'s shirt = the only exception threshold',
      narration: 'Over by the bathroom door, there\'s a bouncer blocking entry. On his shirt: "6.9." He won\'t let bicarb through unless the pH drops below that number. Do NOT give bicarbonate in DKA unless pH is below 6.9. Above that, acidosis self-corrects with insulin and fluids. Giving bicarb when it\'s not needed worsens hypokalemia and paradoxically worsens CNS acidosis.',
      visual: 'Muscular bouncer blocking the bathroom door, "6.9" printed on his shirt, arms crossed in refusal',
      anchor: 'Do NOT give bicarbonate unless pH <6.9 — bicarb worsens hypokalemia and paradoxical CNS acidosis; acidosis self-corrects with insulin and fluids'
    },
    {
      n: 9,
      hook: 'contrast — tiny child-sized chair next to adult furniture encodes pediatric risk; swelling balloon-brain = cerebral edema',
      narration: 'Take a look at the small VIP table in the foreground — a child-sized chair next to the adult furniture, with a balloon shaped like a brain slowly inflating above it. That\'s your cerebral edema warning. In pediatric DKA, dropping glucose too fast causes fatal brain swelling. The rule: don\'t drop glucose faster than 50 to 75 mg/dL per hour in kids. This is the number one cause of death in pediatric DKA.',
      visual: 'Tiny child-sized chair at foreground VIP table, inflating balloon shaped like a brain hovering above it',
      anchor: 'Pediatric DKA: cerebral edema is #1 cause of death; do not drop glucose >50-75 mg/dL/hr; avoid overly aggressive fluid resuscitation in children'
    },
    {
      n: 10,
      hook: 'functional — tip jar overflowing upward (paradoxical rise) encodes how urine ketones rise during treatment',
      narration: 'Finally, check out the tip jar at the end of the bar — it\'s overflowing upward, coins floating out the top like they\'re defying gravity. That\'s the paradox. Urine ketones measure acetoacetate, but in DKA the predominant ketone is beta-hydroxybutyrate. As the patient improves, BHB converts to acetoacetate — so urine ketones actually increase as the patient gets better. Follow serum BHB or the anion gap, never the urine dipstick.',
      visual: 'Tip jar at bar\'s end overflowing upward with coins floating out, defying gravity — the paradoxical rise',
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
  prompt1_sample: 'Speakeasy bar interior, warm amber and deep teal palette, wide-plank wooden floor, brick walls with peeling plaster, heavy timber ceiling beams, bar counter with shelving behind it, chalkboard menu on back wall, wide establishing shot showing full room layout with clear zones far left left center right far right foreground background, spacious enough for 8-10 distinct objects'
};

// ── Demo / operator toggles ──────────────────────────────────────

const demoToggle = document.getElementById('demo-mode-toggle');
const demoBanner = document.getElementById('demo-banner');
demoToggle.addEventListener('change', () => {
  demoBanner.classList.toggle('visible', demoToggle.checked);
});
demoBanner.classList.toggle('visible', demoToggle.checked);

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
      if (code !== null) alert('Incorrect operator access code.');
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

function isRealUserPrompt(topic) {
  const normalized = (topic || '').trim().toLowerCase();
  if (!normalized) return false;
  // Any real typed topic (even a short one like "DKA" or "ACLS") should trigger the
  // demo-override warning; only the placeholder "e.g. …" hint is ignored.
  return !/^e\.g\./.test(normalized) && normalized.length >= 3;
}

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
    narClone?.querySelectorAll('.row-num, .hook-tag').forEach(el => el.remove());
    const hookEl = cells[0]?.querySelector('.hook-tag');
    const hook = hookEl?.textContent?.trim() || '';
    const narration = narClone?.innerText?.trim() || '';
    const visual    = cells[1]?.textContent?.trim() || '';
    const encodes   = cells[2]?.textContent?.trim() || '';
    return `[${i+1}]${hook ? ` HOOK: ${hook}\n    ` : ' '}NARRATION: ${narration}\n    VISUAL: ${visual}\n    ENCODES: ${encodes}`;
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

// Final safety gate before spending a paid image request: guarantee both prompts
// are non-empty and within the model-safe character budget. Returns clamped
// prompts and whether anything had to be trimmed.
function gateImagePrompts(rawP1, rawP2) {
  const clampedP1 = rawP1 ? clampImagePrompt(rawP1) : '';
  const clampedP2 = rawP2 ? clampImagePrompt(rawP2) : '';
  const trimmed = (rawP1 && rawP1.length > clampedP1.length) || (rawP2 && rawP2.length > clampedP2.length);
  return { p1: clampedP1, p2: clampedP2, trimmed };
}

// Antigravity render target: when the operator opts to route to Antigravity, the
// Forge must NOT touch the Gemini API at all (avoids the billing-blocked
// "prepayment credits depleted" path). We stop here with the gated prompts staged
// for the AG agentapi bridge to pick up, rather than making a provider call the
// cloud backend can't fulfill for a local desktop renderer. See ANTIGRAVITY.md.
function handoffToAntigravity(prompts) {
  const status = document.getElementById('gen-img-status');
  const btn = document.getElementById('generate-images-btn');
  // Stage the prompts where the CLI bridge / audit loop can read them; do not POST.
  window.__mnemorizedAntigravityPrompts = prompts;
  window.dispatchEvent(new CustomEvent('mnemorized:antigravity-handoff', { detail: { prompts } }));

  setStatus('prompt', '✦ Ready for Antigravity', 'done');
  setStageDetail('prompt', `Gemini API skipped. ${prompts.length} gated prompt(s) staged for Antigravity — run the agentapi bridge (tools/Invoke-AntigravityAgentApi.ps1) to render, then audit against the rubric.`);
  showBody('prompt');
  const handoffTitle = document.getElementById('handoff-title');
  const handoffText = document.getElementById('handoff-text');
  const handoffMsg = document.getElementById('handoff-message');
  if (handoffTitle) handoffTitle.textContent = 'Prompts staged for Antigravity';
  if (handoffText) handoffText.textContent = 'The Gemini API call was skipped. Copy the image prompts below into the Antigravity render loop.';
  if (handoffMsg) handoffMsg.style.display = '';
  if (status) { status.textContent = `✓ ${prompts.length} prompt(s) staged for Antigravity — Gemini skipped`; status.style.color = 'var(--teal)'; }
  if (btn) { btn.disabled = false; btn.innerHTML = '✦ Generate Images'; }
  console.info('[Mnemorized] Antigravity render target: Gemini skipped; prompts staged on window.__mnemorizedAntigravityPrompts.');
}

async function generateImages() {
  const gate = gateImagePrompts(
    document.getElementById('prompt-copy-1')?.value,
    document.getElementById('prompt-copy-2')?.value
  );
  const p1 = gate.p1;
  const p2 = gate.p2;
  if (!p1 && !p2) { alert('Forge a palace first to generate image prompts.'); return; }
  if (gate.trimmed) {
    // Persist the clamped versions so what we send matches what the user sees and
    // copies. (setStageDetail below is overwritten immediately, so note it on the
    // durable prompt panels instead.)
    if (p1) { document.getElementById('prompt-copy-1').value = p1; document.getElementById('img-prompt-1').textContent = p1; }
    if (p2) { document.getElementById('prompt-copy-2').value = p2; document.getElementById('img-prompt-2').textContent = p2; }
    console.warn('[Mnemorized] Image prompt exceeded the safe length budget and was trimmed before sending to Gemini.');
  }

  // Render-target fork: Antigravity mode never calls the Gemini API. Branch before
  // the backend/Gemini readiness checks so a billing-blocked or unconfigured Gemini
  // key does not stop an Antigravity render.
  if (document.getElementById('image-target-antigravity')?.checked) {
    const btn = document.getElementById('generate-images-btn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Staging…'; }
    handoffToAntigravity([p1, p2].filter(Boolean));
    return;
  }

  if (forgeReplayMode !== 'replay') {
    if (!backendState.checked) await refreshBackendStatus();
    if (!backendState.reachable) { openConnectionModal(); return; }
    if (!backendState.providerAuthReady) { openConnectionModal(); return; }
    if (!backendState.geminiConfigured) {
      openConnectionModal();
      syncConnectionModal('Backend reachable, but GEMINI_API_KEY is not configured on the server yet.');
      return;
    }
  }

  const btn = document.getElementById('generate-images-btn');
  const status = document.getElementById('gen-img-status');
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Generating…'; btn.style.borderColor = ''; btn.style.color = ''; }
  if (status) status.textContent = 'Sending prompts to Gemini…';

  setStatus('prompt', '✦ Generating image…', 'running');
  setStageDetail('prompt', 'Gemini is illustrating your memory palace. This may take up to 60 seconds.');
  showBody('prompt');
  const handoffTitle = document.getElementById('handoff-title');
  const handoffText = document.getElementById('handoff-text');
  const handoffMsg = document.getElementById('handoff-message');
  if (handoffTitle) handoffTitle.textContent = 'Generating your memory palace…';
  if (handoffText) handoffText.textContent = 'Gemini is illustrating the scene with all anchors. This may take up to 60 seconds.';
  if (handoffMsg) handoffMsg.style.display = '';

  document.getElementById('gen-img-1').style.display = 'none';
  document.getElementById('gen-img-2').style.display = 'none';
  const resultContainer = document.getElementById('gen-img-result');
  if (resultContainer) resultContainer.style.display = 'none';

  const prompts = [p1, p2].filter(Boolean);

  // Force-refresh the token — the pipeline may have run for minutes and the JWT expired
  if (typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
    try {
      const { data: refreshed } = await supabaseClient.auth.refreshSession();
      if (refreshed?.session) {
        authState.session = refreshed.session;
      }
    } catch (_) { /* best-effort — the 401 retry below will catch it */ }
  }

  const headers = {
    'Content-Type': 'application/json',
    ...getReplayHeaders('stage4-gemini-image'),
  };
  if (authState.session?.access_token) {
    headers.Authorization = `Bearer ${authState.session.access_token}`;
  }

  const TRANSIENT_CODES = new Set([502, 503, 504]);
  const MAX_RETRIES = 1;

  async function attemptImageGen() {
    let res;
    try {
      res = await fetch(getApiUrl('/api/generate-image'), {
        method: 'POST',
        headers,
        body: JSON.stringify({ prompts })
      });
    } catch (fetchErr) {
      backendState.reachable = false;
      setBackendBadge('offline', '⚠ PROXY OFFLINE');
      throw new Error(`Proxy unavailable: ${fetchErr.message}`);
    }

    // 401 → refresh token and retry once
    if (res.status === 401 && typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
      const { data: refreshData } = await supabaseClient.auth.refreshSession();
      if (refreshData?.session?.access_token) {
        authState.session = refreshData.session;
        headers.Authorization = `Bearer ${refreshData.session.access_token}`;
        res = await fetch(getApiUrl('/api/generate-image'), {
          method: 'POST',
          headers,
          body: JSON.stringify({ prompts })
        });
      }
    }

    if (res.status === 401) {
      openAuthModal();
      throw new Error('Sign in to generate images.');
    } else if (res.status === 402) {
      const quota = await res.json().catch(() => ({}));
      throw new Error(getQuotaExceededMessage(quota));
    } else if (res.status === 503) {
      throw new Error('GEMINI_API_KEY is not configured on the backend.');
    }
    return res;
  }

  try {
    let res;
    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
      res = await attemptImageGen();
      if (res.ok || !TRANSIENT_CODES.has(res.status) || attempt === MAX_RETRIES) break;
      if (status) status.textContent = 'Gemini hiccup — retrying…';
      await new Promise(r => setTimeout(r, 2000 * (attempt + 1)));
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = err.error?.message || `Image generation failed (HTTP ${res.status}).`;
      const isSafety = err.error?.type === 'safety_block' || (err.prompt_errors || []).some(e => e.type === 'safety_block');
      if (isSafety) {
        throw new Error('Gemini blocked the image prompt for safety/content policy. Try rephrasing the scene with less graphic clinical language, then hit Regenerate.');
      }
      throw new Error(msg);
    }

    const data = await res.json();
    const images = data.images || [];
    const promptErrors = data.prompt_errors || [];

    images.forEach((img, i) => {
      const n = i + 1;
      const container = document.getElementById(`gen-img-${n}`);
      const el = document.getElementById(`gen-img-${n}-el`);
      if (container && el) {
        el.src = `data:${img.mime_type};base64,${img.data}`;
        container.style.display = 'block';
      }
    });

    const finalImage = images.length >= 2 ? images[images.length - 1] : images[0];
    const resultEl = document.getElementById('gen-img-result-el');
    if (resultContainer && resultEl && finalImage) {
      resultEl.src = `data:${finalImage.mime_type};base64,${finalImage.data}`;
      resultContainer.style.display = 'block';
      window.MnemorizedGuided?.onImageReady?.(resultEl.src);
    }

    if (handoffMsg) handoffMsg.style.display = 'none';

    if (images.length > 0 && promptErrors.length > 0) {
      const failedIdx = promptErrors.map(e => e.prompt_index + 1).join(', ');
      if (status) { status.textContent = `✓ ${images.length} image(s) — prompt ${failedIdx} failed`; status.style.color = 'var(--gold)'; }
      setStatus('prompt', '⚠ Partial success', 'done');
      setStageDetail('prompt', `${images.length} image(s) generated. Prompt ${failedIdx} failed: ${promptErrors[0].message}`);
    } else if (images.length > 0) {
      if (status) { status.textContent = `✓ ${images.length} image${images.length !== 1 ? 's' : ''} generated`; status.style.color = 'var(--green)'; }
      setStatus('prompt', '✓ Palace illustrated', 'done');
      setStageDetail('prompt', 'Your memory palace image is ready. Download it or regenerate for a different result.');
    } else {
      throw new Error('No images were generated. Try regenerating.');
    }
  } catch (err) {
    if (status) { status.textContent = `✗ ${err.message}`; status.style.color = '#f56565'; }
    if (handoffTitle) handoffTitle.textContent = 'Image generation failed';
    if (handoffText) handoffText.textContent = err.message;
    setStatus('prompt', '✗ Image failed', 'error');
    setStageDetail('prompt', err.message);
    console.error('Image generation error:', err);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '⟳ Retry Image Generation';
      btn.style.borderColor = 'rgba(245,200,66,.6)';
      btn.style.color = 'var(--gold)';
    }
    return;
  }
  if (btn) { btn.disabled = false; btn.innerHTML = '✦ Generate Images'; }
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

function downloadForgeBundle() {
  const topic = document.getElementById('topic')?.value?.trim() || '';
  if (!topic && !currentStoryData) { alert('Forge a palace first.'); return; }

  const qualityResultEl = document.getElementById('quality-result');
  const qualitySummary = qualityResultEl?.innerText?.trim() || '';

  const img1 = document.getElementById('gen-img-1-el');
  const img2 = document.getElementById('gen-img-2-el');
  const resultImg = document.getElementById('gen-img-result-el');

  const bundle = {
    _format: 'mnemorized-forge-bundle-v1',
    exported_at: new Date().toISOString(),
    topic: topic,
    model: CLAUDE_MODEL,
    sketchy_style_prompt: SKETCHY_STYLE,
    anti_meta_text: ANTI_META_TEXT,
    story: currentStoryData || null,
    image_prompts: {
      prompt1: document.getElementById('prompt-copy-1')?.value || '',
      prompt2: document.getElementById('prompt-copy-2')?.value || '',
    },
    quality_gate: qualitySummary,
    generated_images: {
      image_1: (img1?.src && img1.src.startsWith('data:')) ? img1.src : null,
      image_2: (img2?.src && img2.src.startsWith('data:')) ? img2.src : null,
      final: (resultImg?.src && resultImg.src.startsWith('data:')) ? resultImg.src : null,
    },
    guided_video: window.MnemorizedGuided?.getBundleData?.() || null,
  };

  const json = JSON.stringify(bundle, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  const safeName = topic.replace(/[^a-zA-Z0-9]+/g, '_').substring(0, 40) || 'forge';
  a.download = `${safeName}_bundle.json`;
  a.click();
  URL.revokeObjectURL(a.href);
}

async function rebuildImagePromptsForStory(storyData) {
  if (!storyData?.voLines?.length) {
    setStatus('prompt', 'No repaired story', 'error');
    setStageDetail('prompt', 'Image prompts could not be rebuilt because the repaired script has no anchors.');
    return;
  }

  const topic = document.getElementById('topic')?.value?.trim() || 'medical topic';
  const n = storyData.voLines.length;

  setStatus('prompt', 'Rebuilding image prompts...', 'running');
  setStageDetail('prompt', 'Rebuilding constitution-guided illustration prompts from the repaired anchor script.');

  try {
    const pair = await buildImagePromptPair(
      topic,
      storyData,
      'repair',
      'repair-gemini-prompt-director',
      'repair-image-prompt'
    );
    renderImagePromptPair(
      storyData,
      pair,
      '✓ Rebuilt from repaired script',
      `Illustration handoff rebuilt with ${n} repaired anchors using ${pair.director === 'gemini' ? 'Gemini constitution director' : 'fallback prompt composer'}.`
    );
  } catch (error) {
    setCurrentPalaceData(storyData, '', '');
    // Blank the visible/copy prompt fields too, so "Generate Images" cannot
    // silently illustrate from the stale pre-repair prompts still on screen.
    ['img-prompt-1', 'img-prompt-2'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = '';
    });
    ['prompt-copy-1', 'prompt-copy-2'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    setStatus('prompt', `Prompt rebuild failed: ${error.message}`, 'error');
    setStageDetail('prompt', 'The repaired script was kept, but image prompts must be rebuilt before generating — click Forge again or re-run the prompt step.');
  }
}

async function repairStoryVisualFormat(xmlText, validation, options = {}) {
  const errors = (validation?.fatal || []).join('\n- ');
  if (!xmlText || !errors) return '';
  // When the only remaining fatals are VISUALs over the hard word cap, escalate to
  // a focused length-repair: a general repair pass often leaves a dense anchor one
  // or two words over, and a single word-count fatal must not abort a complete scene.
  const lengthDirective = options.lengthOnly
    ? `\n\nCRITICAL LENGTH REPAIR: The only remaining problems are VISUAL fields over the hard word cap. Compress ONLY the named over-length VISUAL fields to 24 words or fewer each. Do NOT shorten by dropping clinical facts — move every number, dose, threshold, and detail into that same anchor's NARRATION and ANCHOR. Leave every already-valid VISUAL and all other fields byte-for-byte unchanged.`
    : '';
  const body = {
    model: CLAUDE_MODEL,
    max_tokens: 6144,
    system: `You repair XML medical memory-palace scripts for visual format only.

Return ONLY the full corrected XML. Preserve scene_title, opening, anchor count, narration medical facts, anchors, and review_script substance.

Only rewrite VISUAL fields and review_script image references when necessary.
Rules for every VISUAL:
- 24 words or fewer.
- One compact physical drawing instruction.
- One main object or character interaction plus one location phrase.
- No arrow glyphs, speech bubbles, checklist rows, multi-label signs, or more than one text-bearing surface.
- Move excess medical detail into NARRATION or ANCHOR; do not delete clinical facts.`,
    messages: [{
      role: 'user',
      content: `Fix these validation errors:\n- ${errors}${lengthDirective}\n\nOriginal XML:\n${xmlText}`
    }]
  };
  const res = await claudeFetch(body, 'stage2-story-visual-micro-repair');
  const rawText = await res.text().catch(() => '(could not read body)');
  const box = document.getElementById('debug-box');
  if (box) {
    box.style.display = 'block';
    box.textContent = `── STORY VISUAL MICRO-REPAIR — HTTP ${res.status} ──\n${rawText.slice(0, 2000)}`;
  }
  if (!res.ok) return '';
  const raw = JSON.parse(rawText);
  return parseProviderContent(raw, 'Scene Narrative visual micro-repair');
}

// ── Main pipeline ────────────────────────────────────────────────

async function runPipeline() {
  const topic    = document.getElementById('topic').value.trim();
  const chaos    = parseInt(slider.value);
  const artStyle = document.getElementById('style-select').value;
  const tone     = document.querySelector('#tone-chips .chip.active')?.dataset.val || 'visceral and cinematic';

  if (!topic) { alert('Please describe what needs to be memorized in Section I. Do not include patient-identifying information.'); return; }
  if (isDemoMode() && isRealUserPrompt(topic)) {
    const useDemo = confirm(
      'Demo mode is on and will ignore your Section I prompt, loading the built-in DKA sample instead. Turn Demo off to forge this topic.\n\nContinue with the demo sample anyway?'
    );
    if (!useDemo) {
      demoToggle.checked = false;
      demoBanner.classList.remove('visible');
      return;
    }
  }

  currentStoryData = null;
  currentPromptData = { prompt1: '', prompt2: '' };
  currentQualityGateData = null;
  window.MnemorizedGuided?.reset?.();
  refreshAuthUI();

  // Resolve the structured lesson blueprint (if the guided builder produced one
  // that still matches this topic). It gives Stage 1 an explicit scope contract
  // and the quality gate an independent must-cover anchor contract.
  const lessonSpec = window.MnemorizedLessonSpec?.getActiveLessonSpec?.(topic) || null;
  const lessonBlueprintText = lessonSpec
    ? window.MnemorizedLessonSpec.lessonSpecToPromptText(lessonSpec)
    : '';

  const btn = document.getElementById('forge-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span> MNEMORIZING…';

  document.getElementById('pipeline').classList.add('visible');
  setStatus('story', 'Waiting…', '');
  setStatus('quality', 'Waiting…', '');
  setStatus('prompt', 'Waiting…', '');
  setStageDetail('story', 'Waiting to build the clinical fact map and memory palace script.');
  setStageDetail('quality', 'Runs after the script when sign-in and private medical retrieval are available.');
  setStageDetail('prompt', 'Runs after the script is generated and checked.');

  // ══ DEMO MODE — full UI flow, zero API calls ══════════════════
  if (isDemoMode()) {
    const D = DEMO_DATA;

    setStatus('story', '✦ Writing scene…', 'running');
    setStageDetail('story', 'Demo mode is loading the sample DKA palace without contacting AI providers.');
    await demoDelay(1800);

    showBody('story');
    document.getElementById('story-header').innerHTML =
      `<div class="story-scene-title">${escapeHtml(D.scene_title)}</div>
       <div class="story-opening">${escapeHtml(D.opening)}</div>`;

    document.getElementById('vo-body').innerHTML = D.voLines.map(v => `
      <tr>
        <td><span class="row-num">${v.n}</span>${v.hook ? `<div class="hook-tag">${escapeHtml(v.hook)}</div>` : ''}${formatNarrationHtml(v.narration)}</td>
        <td>${escapeHtml(v.visual)}</td>
        <td class="encodes-cell">${escapeHtml(v.anchor)}</td>
      </tr>`).join('');
    document.getElementById('vo-table-wrap').style.display = 'block';

    document.getElementById('review-text').innerHTML = formatReviewBullets(D.review_script);
    document.getElementById('review-wrap').removeAttribute('open');
    document.getElementById('review-wrap').style.display = 'block';

    setStatus('story', '✓ Complete', 'done');
    setStageDetail('story', `${D.voLines.length} sample anchors generated with a rapid review script.`);
    await demoDelay(800);
    setStatus('quality', 'Demo skipped', 'done');
    setStageDetail('quality', 'Demo mode skips private medical retrieval and provider calls.');
    renderQualityGateMessage('Demo mode uses built-in sample content, so private medical retrieval is skipped.', 'success');
    await demoDelay(400);

    setStatus('prompt', '✦ Building image prompts…', 'running');
    setStageDetail('prompt', 'Preparing illustration handoff prompts from the sample scene.');
    await demoDelay(1200);

    const n = D.voLines.length;
    const assigned = assignZones(D.voLines);

    const demoP1Raw = SKETCHY_STYLE_ROOM + '\n\n' + D.prompt1_sample + ', aspect ratio 16:9, flat 2D cartoon';

    const demoP2Raw = SKETCHY_STYLE + '\n\n' + D.prompt1_sample +
      ', aspect ratio 16:9, flat 2D cartoon.\n\n' +
      `${ANTI_META_TEXT}\n\n` +
      `SCENE OBJECT RULE: Do NOT label or name any part of the room itself. ` +
      `Background surfaces are unlabeled.\n\n` +
      `Add ALL ${n} of the following medical mnemonic anchors to the scene. ` +
      `Anchors may be objects, characters/figures, or interactive elements — they are VISUAL MNEMONICS, not labeled props. ` +
      `Preserve clear spatial hierarchy: left/center/right/foreground/background zones must stay readable and uncluttered. ` +
      `Each anchor should be recognizable by its SHAPE and SILHOUETTE first. ` +
      `${ANCHOR_LEGIBILITY_RULE} ` +
      `Text labels are secondary and optional — if present, maximum 3 words per ordinary mnemonic name label. ` +
      `${NO_PRECISION_TEXT_RULE} ` +
      `${EXACT_LABEL_RULE} ` +
      `SCENE TEXT BUDGET: at most 12 short mnemonic name labels in the ENTIRE image, and ZERO numeric/dose/threshold/formula text. Character names count. ` +
      `Weave ALL of them into ONE flowing scene, written as continuous prose describing a single wide shot — a narrator walking the room, never a bulleted or tagged list:\n\n` +
      buildImageAnchorLines(assigned) + '\n\n' +
      `All ${n} anchors must be present, visually distinct, and each rendered EXACTLY ONCE — do not duplicate, mirror, or repeat any anchor object or figure anywhere else in the scene. ` +
      `Do NOT add labels to room surfaces, walls, beams, or background objects. ` +
      `Maintain same lighting, color palette, and atmosphere.\n\n` +
      buildTextAllowlistFence(assigned);

    // Clamp the same way the live pipeline does so the demo can't display or copy
    // a prompt longer than the model-safe budget.
    const demoP1 = clampImagePrompt(demoP1Raw);
    const demoP2 = clampImagePrompt(demoP2Raw);

    showBody('prompt');
    if (isOperatorMode()) operatorPanel.classList.add('visible');
    document.getElementById('img-prompt-1').textContent = demoP1;
    document.getElementById('img-prompt-2').textContent = demoP2;
    document.getElementById('prompt-copy-1').value = demoP1;
    document.getElementById('prompt-copy-2').value = demoP2;
    setStatus('prompt', isOperatorMode()
      ? `✓ 2 prompts ready (${n} anchors in single pass)`
      : '✓ Image prompts ready', 'done');
    setStageDetail('prompt', `Illustration handoff ready with ${n} anchors.`);
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
    window.MnemorizedGuided?.onStoryReady?.(currentStoryData);

    btn.disabled = false; btn.innerHTML = '✦ FORGE PALACE';
    return;
  }
  // ══ END DEMO MODE ═════════════════════════════════════════════

  function showDebug(label, data) {
    const box = document.getElementById('debug-box');
    box.style.display = 'block';
    box.textContent = `── ${label} ──\n${typeof data === 'string' ? data : JSON.stringify(data, null, 2)}`;
  }

  function parseAPIResponse(raw, context) {
    showDebug(context + ' — raw API response', raw);
    const text = parseProviderContent(raw, context);
    document.getElementById('debug-box').style.display = 'none';
    return text;
  }

  function isDenseProtocolTopic(topicText, concepts = []) {
    const haystack = `${topicText || ''}\n${(concepts || []).join('\n')}`.toLowerCase();
    return /\b(nihss|stroke scale|score|scoring|scale|protocol|algorithm|criteria|classification|staging|checklist|items?|steps?)\b/.test(haystack)
      || (concepts || []).length >= 10;
  }

  // ── STAGE 1: Clinical Context (with evidence grounding) ──
  const evidenceAvailable = !!((authState.user || appConfig.demoAuthBypass) && appConfig.medicalKnowledgeEnabled && backendState.medicalKnowledgeConfigured);
  if (evidenceAvailable) {
    setStatus('story', '✦ Retrieving source evidence…', 'running');
    setStageDetail('story', 'Searching private medical knowledge base before generating concepts.');
  } else {
    setStatus('story', '✦ Analyzing topic…', 'running');
    setStageDetail('story', 'Extracting high-yield clinical concepts and a spatial scene plan.');
  }
  let clinicalContext = '';
  let coreConcepts = [];
  const evidenceHeaders = evidenceAvailable ? {
    'x-evidence-grounding': 'true',
    'x-evidence-topic': encodeHeaderValue(topic),
  } : {};
  try {
    const ctxRes = await claudeFetch(withAdvisor({
        model: CLAUDE_MODEL,
        max_tokens: 1200,
        system: `You are a senior clinical educator and board exam question writer designing original visual mnemonic memory scenes. Extract the essential teaching points for a silhouette-first mnemonic scene. Be EXHAUSTIVE — if a concept is commonly tested on USMLE, COMLEX, shelf exams, or in-training exams, it MUST be included.

COMPLETENESS CHECK: Before finalizing, verify you have not omitted any major category. For example:
- For scoring systems: every sub-item and its specific scoring range
- For interpretation algorithms: every step in the systematic approach
- For drug classes: mechanism, indications, contraindications, key side effects, monitoring
- For pathophysiology: etiology, pathogenesis, clinical features, diagnosis, management, complications
- For procedures/protocols: indications, contraindications, steps, complications, alternatives

When SOURCE EVIDENCE is provided below, derive your core concepts primarily from that material. Use the exact terminology, thresholds, and clinical details from the source. You may supplement with critical safety facts from your own knowledge, but prioritize source-grounded facts.
${lessonBlueprintText ? `\n${lessonBlueprintText}\n\nStay inside this blueprint's scope: cover every MUST category, and do NOT expand into the out-of-scope areas unless the topic clearly demands it.\n` : ''}
Output ONLY these two XML tags, nothing else:

<core_concepts>The 8-12 most important, data-backed clinical facts that MUST be encoded — aim for comprehensive board-level coverage with ZERO important omissions. One per line. Include: diagnostic criteria, key thresholds/numbers, mechanism, first-line management steps, critical safety checks, common pitfalls, and resolution/disposition criteria. EVERY specific number, threshold, dose, duration, angle, and scoring range must be EXACT per current guidelines — no approximations, no rounding, no merging different values into one. If the topic has a well-known systematic approach (e.g. EKG interpretation steps, trauma primary survey), cover EVERY step — do not skip any.</core_concepts>
<scene_logic>How to spatially arrange these concepts in a single illustrated scene — how the eye moves left-to-right and foreground-to-background. 8-10 anchors need distinct zones across left, center, right, foreground, and background areas.</scene_logic>`,
        messages: [{ role: 'user', content: `Clinical topic: ${topic}\nLearner: ${lessonSpec?.learner || 'ED/ICU physician'} — needs precise, high-yield anchors.` }]
      }), 'stage1-clinical-context', evidenceHeaders);
    setStatus('story', '✦ Analyzing topic…', 'running');
    setStageDetail('story', 'Extracting high-yield clinical concepts and a spatial scene plan.');
    const ctxRaw = await ctxRes.json();
    const ctxTxt = parseProviderContent(ctxRaw, 'Clinical Context');
    const core   = extractXmlTag(ctxTxt, 'core_concepts');
    const logic  = extractXmlTag(ctxTxt, 'scene_logic');
    if (core || logic) {
      const blueprintSuffix = lessonBlueprintText ? `\n\n${lessonBlueprintText}` : '';
      clinicalContext = `CLINICAL DESIGN CONTEXT — bake these facts and spatial logic into the scene:\n\nCORE CONCEPTS:\n${core}\n\nSCENE LAYOUT:\n${logic}\n\nEvery anchor must encode a specific fact from above.${blueprintSuffix}`;
      coreConcepts = core.split('\n').map(l => l.replace(/^[-•*\d.)\s]+/, '').trim()).filter(Boolean).slice(0, 12);
    }
  } catch(e) {
    console.warn('Clinical context extraction failed (non-fatal):', e.message);
  }

  // ── STAGE 2: Voiceover Script ─────────────────────
  setStatus('story', '✦ Writing scene…', 'running');
  setStageDetail('story', 'Writing narration, visual anchors, encoded facts, and the rapid review script.');

  const storySystem = `You are writing narration for an original medical visual mnemonic memory palace. The scene is a single static illustration — there is no animation or movement. The narrator is an unseen voice pointing things out directly to a medical student viewer. There is no narrator or tour-guide character — but MNEMONIC CHARACTERS (figures whose names, shapes, or actions encode medical facts) are encouraged. Characters should be the concepts themselves, not guides explaining them.

SCENE SETTING — YOU CHOOSE:
- Strongly prefer an ORIGINAL phonetic pun or sound-alike for a key term in the medical topic, but do not force a bad pun. If no clean pun exists, choose a thematic setting whose physical layout teaches the topic.
- Do NOT reuse named scenes, recurring characters, or fixed fact→symbol maps from existing commercial visual mnemonic products (that is the only IP line). Invent fresh SCENES and CHARACTER NAMES — but the sanctioned universal metaphors (banana = potassium, etc.) are Mnemorized's own approved vocabulary and should still be used freely.
- Made of materials that render flat: wood, paper, brick, chalkboard, fabric, cork, cardboard, stone, ceramic
- BEST settings: bars, pubs, workshops, kitchens, old shops, speakeasies, market stalls, barber shops, diners, courtrooms, train stations
- AVOID: glass, chrome, metal, screens, modern clinical equipment, sci-fi technology, holographic displays — these fight the flat hand-drawn style
- The setting is a spatial memory map, not a backdrop. Each anchor occupies a memorable zone. Anchors should mostly fit the environment — but a SANCTIONED metaphor (banana = potassium, baking-soda box = bicarbonate, etc.) is placed even when it is out of place in the theme; do not sacrifice a strong universal cue just to keep the scene thematically tidy.

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
- WHERE EXACT VALUES LIVE: the IMAGE never prints numbers/doses/units/thresholds/formulas. Every exact value is stated in NARRATION (spoken aloud) and recorded in ANCHOR (the flashcard). The VISUAL only carries the hook; the precise figure is heard and read, not drawn — this is how Picmonic/Sketchy handle doses (symbol in the sketch, number in the narration + fact list).

COMPLETENESS — NON-NEGOTIABLE:
- Before writing anchors, mentally enumerate EVERY major category, classification, or step in the topic
- If the topic is a scoring system, EVERY item must be covered (group related items but do not skip any)
- If the topic is a stepwise process (e.g. EKG interpretation, ACLS algorithm), EVERY step must appear — do not skip steps even if they seem "obvious"
- If the topic has a classification system (e.g. types of heart block), include ALL types including the most severe/dangerous one
- Common omission errors to avoid: skipping complete/3rd-degree heart block when covering AV blocks, omitting the most severe classification tier, forgetting disposition/resolution criteria, leaving out common exceptions to rules
- After writing all anchors, review them against the topic and ask: "Is there a major testable fact or category I missed?" If yes, add another anchor.

VISUAL MNEMONIC DESIGN — THIS IS THE HEART OF THE PRODUCT:
These principles are inspired by visual mnemonic education. The goal: a student recalls the medical fact from the SHAPE, IDENTITY, RELATIONSHIP, and POSITION of the cue even with ALL text removed. Originality applies to SCENES, CHARACTER NAMES, LAYOUTS, and phonetic puns — do NOT copy proprietary curated symbol systems (named scenes, recurring characters, or fixed fact→symbol maps from commercial mnemonic products). It does NOT mean avoiding common-knowledge associations: the SANCTIONED metaphors below are Mnemorized's own approved vocabulary and MUST be used (banana = potassium is global medical culture, not proprietary). Never fall back to a bare text label when a sanctioned metaphor or a shape/function analogy exists.

SANCTIONED VISUAL METAPHOR LIBRARY — fixed, approved, common-knowledge cues. USE THESE FIRST whenever the concept appears, and keep them consistent across every topic (banana = potassium everywhere). They are always preferred over a text label:
${VISUAL_METAPHOR_LIBRARY}

ENCODING HIERARCHY — try each level in order, use the FIRST that fits. Only drop to LABELED TEXT after genuinely failing levels 1-6:
1. PURE VISUAL METAPHOR (strongest — no text needed): use an instantly-recognizable object from the SANCTIONED library above (or an equally universal common-knowledge association) so the anchor reads by silhouette alone. banana bunch = potassium, salt sack/shaker = sodium/saline, household box of baking soda = bicarbonate, golden honey/sugar cubes = glucose, padlock = restricted/hold, skull = toxicity. Oversize the object. Reach for this FIRST for any electrolyte, ion, drug, fluid, or hazard that has a library entry — a barrel merely STAMPED "NaCl" or "K+" is a failure when a salt sack or banana bunch conveys it.
   METAPHOR BEATS THEME: a sanctioned metaphor ALWAYS wins over scene-theme coherence. If the setting is a medieval mill and the fact is potassium, still draw a giant bunch of BANANAS; if it is bicarbonate, draw a household BAKING-SODA BOX — even though those objects are "out of place" in that setting. An incongruous, oddly-placed object is MORE memorable (the bizarreness effect), not less. NEVER swap a sanctioned metaphor for a theme-matching generic prop (barrel, cart, crate, sack) plus a text label. Do NOT render a drug or electrolyte as a "barrel labelled INSULIN / NaHCO3 / K+" — that is the exact failure this rule exists to stop.
2. SOUND-ALIKE: Object or character NAME sounds like the medical term. Invent a fresh phonetic pun (puns and character names are where originality applies — do not reuse a proprietary product's named character). Clean, obvious puns are powerful.
3. LOOK-ALIKE: Object SHAPE mirrors a number, symbol, organ, or process. Fork with 3 prongs → triad. Cracked wall → inhibition. Y-shaped branch → antibody. A figure-8 knot → chromosome 8.
4. FUNCTIONAL ANALOGY: Object BEHAVIOR mirrors the clinical mechanism. Bellows pushing air → bronchodilator. Cork blocking pipe → antagonist. Overflowing bucket → excess/toxicity. Key in lock → agonist. Guard blocking door → immune defense.
5. CONTRAST/THRESHOLD: Two OPPOSING objects encode a decision point. Big vs small, open vs locked, hot vs cold, thumbs-up shelf vs thumbs-down shelf, short rope vs long rope.
6. SPATIAL: POSITION encodes meaning. Escalation goes up (stairs, shelves). Sequence goes left-to-right. Danger is isolated behind barriers. Exit/door = discharge criteria. Basement = last-resort therapy.
7. LABELED TEXT (weakest — LAST RESORT, NAMES ONLY): a sign or tag with a 1-3 word sound-alike NAME. If you resort to this, the anchor is weak — go back and try levels 1-6 harder. This tier is for NAMES only: numbers, doses, units, thresholds, and formulas are NEVER a text tier — they are either encoded as a shape/count hook (level 3) or omitted from the image and spoken. NEVER label a generic barrel/wall/crate when a sanctioned metaphor exists.

CHARACTER DESIGN (encouraged):
- Mnemonic characters are figures whose NAME, APPEARANCE, or ACTION encodes a concept — they are NOT narrators
- A character's name should SOUND LIKE the medical term (e.g., a bartender named "Pred" for prednisone)
- Clothing, size, color, and held objects encode properties (a tiny character = low dose, a giant = high dose)
- A character's action encodes mechanism: blocking a door = antagonist, pouring liquid = secretion, smashing a wall = bactericidal
- Every character must have a distinctive SILHOUETTE — recognizable by shape alone even as a black shadow

SILHOUETTE TEST: If you turned every anchor into a black shadow with no text visible, could the student still identify what it represents? If no → the visual encoding is too weak. Go back to the encoding hierarchy.

OBJECT INTERACTION = CLINICAL RELATIONSHIP:
- Objects touching/connected = synergy or combination therapy
- Object blocking another = inhibition/antagonism
- Object chained to another = required co-administration
- Objects on opposite sides of a barrier = contraindication
- Progressive size increase = dose escalation or worsening severity
- Two objects on a tilting scale = risk-benefit or threshold decision
- Object in a cage/trap = monitoring requirement or boxed warning
- Contact, blocking, containment, distance, scale, elevation, and sequence should show why facts relate to each other.
- The final image should read as one coherent static map with uncluttered anchor zones, not scattered props.
- Every anchor must be large enough to identify at normal 1024px image size. No anchor may become tiny shelf clutter. If a shelf or wall contains multiple anchors, stagger them vertically and give each one enough empty space and scale to read by shape.

SHAPE DIVERSITY RULE: No two anchors may share the same base shape. If you have one jar, no other anchor can be a jar. If you have one character standing, the next character must sit, crouch, or be a completely different body type. Check your anchor list at the end — if two silhouettes would look the same, redesign one.

PRECISION-VALUE RULE (numbers are NOT drawn as text): a rendered number, dose, unit, threshold, lab value, or formula is a flashcard, not a mnemonic — black out all text and the picture must still cue every fact. So the EXACT value goes in NARRATION (spoken) and ANCHOR (the flashcard), never printed in the VISUAL. In the image you have two options only: (a) ENCODE the number as a visual hook — a shape look-alike (a fork's 3 prongs = a triad; a figure-8 knot = chromosome 8) or a small countable quantity of oversized objects (≤ ~5) — or (b) OMIT it from the image entirely and let the narration carry it. A compound value like "0.1 U/kg/hr" or "15-20 mL/kg/hr" is NOT cleanly encodable — do not try to draw it; encode the CONCEPT with a hook (an insulin-dripping ladle, an overflowing fluid barrel) and state the exact rate in NARRATION + ANCHOR. Never write the digits on a plaque, dial, gauge, or chalkboard.

LARGE NUMBER RULE: Do NOT encode numbers greater than ~5 by asking for exact repeated object counts (generators cannot draw exactly 30 soldiers or 90 items) AND do NOT fall back to stamping the number as text. Use ONE strong oversized object whose scale/action signals "a lot / high / escalating," and put the exact number in NARRATION + ANCHOR.

HOOK/VISUAL CONSISTENCY RULE: An anchor's VISUAL must pass the cover-the-text test on its own — its shape/identity/interaction carries the memory. If an anchor "needs" a printed number or formula to be understood, its hook is too weak: redesign the hook, and move the exact value to NARRATION + ANCHOR.

SCENE TEXT BUDGET: The ENTIRE scene should have at most 12 short mnemonic name labels (sound-alike character/object names, 1-3 words each) and ZERO numeric/dose/threshold/formula text. Prioritize: sound-alike character names > optional flavor labels. Exact numbers never count against this budget because they never appear in the image.

EXACT LABEL RULE: If a visual specifies a short label, copy it exactly. Do not invent alternate spellings, abbreviations, or nonsense words. Sound-alike character names must appear exactly when the name carries the mnemonic. If exact text would be too small or uncertain, replace it with a larger physical symbol instead of misspelling it.

WHAT TO AVOID:
- Plain checklists, generic posters, ordinary clipboards, labeled bottles — these fail the silhouette test
- Any anchor whose ONLY mnemonic value is text printed on it
- Medical equipment used literally (stethoscope for "auscultation" is lazy — use a giant ear trumpet or a character with comically oversized ears)
- Long text strings on any surface — the image generator cannot reliably render more than 3-4 words per label
- Multiple jars, bottles, or containers that would look identical as silhouettes — each anchor needs a unique shape

VISUAL DESCRIPTION RULES:
- MAXIMUM 30 WORDS per visual description
- Aim for at most ONE visible text element per anchor, and it may only be a short sound-alike NAME (1-3 words). Numbers, doses, units, thresholds, and formulas are NOT text elements you may draw — they are spoken/carded.
- Do not cram a list of labels into one visual. If an anchor needs several facts, encode them all with shape/scale/position/action/count; reserve text only for one short mnemonic name, and never for a numeric value.
- If the VISUAL starts turning into a label list, simplify it into one stronger object interaction.
- Describe the mnemonic device, its encoding strategy, and its position — text labels are OPTIONAL (1-3 words max if present)
- VISUAL must describe only what should be drawn. Do not include meta commentary such as "no text labels", "single text element", or "two text elements".
- The visual MUST work even if all text were removed — shape and identity carry the memory
- Do NOT describe: era-specific aesthetics, materials, atmospheric details, lighting effects
- Do NOT use: holographic, translucent, glowing, 3D, projection, transparent, neon-lit, LED
- GOOD: "Giant ant character inspecting three overflowing buckets at center workbench" (ant = Anthonisen, 3 buckets = triad criteria, overflowing = sputum)
- GOOD: "Two bellows — small one pumping fast, large one pumping slow — hanging from ceiling hooks" (dual bronchodilator therapy, size = relative dosing)
- BAD: "Clipboard labeled 'ANTHONISEN' with checklist: 'DYSPNEA / SPUTUM / PURULENCE'" (text-dependent, fails silhouette test, too many words for image generator)

ANCHOR FIELD RULES:
- ANCHOR is the clinical fact only. No "get it", no mnemonic explanation, no scene description, no teaching aside.
- Keep ANCHOR to one crisp sentence under 35 words.
- Put memory-scene explanation in NARRATION, not in ANCHOR.

ABSURDITY LEVEL: ${chaos}/10 — dial how strange the visual anchors are, not how dramatic the narration is.

${clinicalContext}

Respond using ONLY these XML tags in order. Write freely inside — no JSON:
Do not include <thinking>, markdown, analysis, planning notes, headings, or commentary outside these XML tags.

<scene_title>Short evocative title for the memory scene</scene_title>

<opening>2-3 sentences introducing the scene. Set the location and overall vibe conversationally — like "Our scene today takes place at..." or "Welcome to...". Do not describe action or movement.</opening>

For each memory anchor output one <vo_line> block. Aim for 8-10 anchors total — cover the topic comprehensively at board-exam level with dense, original visual mnemonics. Do not stop at 5-6 if there are more high-yield facts to encode.

GROUPING RULE: If a topic has many sub-items (e.g. a scoring system with 15 items, a drug class with 12 side effects), combine closely related sub-items into a SINGLE anchor with one visual element that encodes 2-3 facts together. For example: a scoring scale's "questions" and "commands" sub-items can share one visual station; motor arm and motor leg can share one stopwatch display; language and articulation can share one communication desk. This keeps the total anchor count at 8-10 while still covering every testable fact. Each visual should encode MORE information, not less — denser per anchor, fewer total anchors.

CRITICAL: When grouping sub-items, do NOT lose specificity. If two sub-items have DIFFERENT numbers (different scoring ranges, time limits, angles, doses), the NARRATION and ANCHOR must state BOTH distinct values separately — never collapse them into one number. The VISUAL encodes the two as DISTINCT hooks (e.g. a short stub vs a long pole, a nearly-empty vs a brimming vessel) so they read apart by shape — it does NOT print "10 SEC" and "5 SEC"; those exact values are spoken and carded, not drawn.
ANCHOR COUNT HARD STOP: Never output more than 10 <vo_line> blocks. If you find an 11th fact, merge it into the closest existing anchor before responding.
<vo_line>
HOOK: [sound-alike | look-alike | functional | contrast | spatial] — one sentence: what encodes what and why
NARRATION: [2-4 sentences. Direct viewer attention → name the element → explain the mnemonic link explicitly ("get it? X sounds like Y" or "notice how the shape of X looks like Y") → teach the clinical fact. Natural spoken rhythm. No dramatic language. No movement descriptions.]
VISUAL: [MAXIMUM 30 WORDS. Mnemonic device + encoding strategy + position. Text labels optional (1-3 words max). No era styling, materials, lighting.]
ANCHOR: [Clinical fact only. One crisp line under 35 words. No mnemonic wording, no "get it", no scene description.]
</vo_line>

<review_script>
Rapid-fire recall. One line per anchor. Format: "When you see [image element] — remember [clinical fact]"
</review_script>`;

  const storyUser = `Create an original visual mnemonic memory palace narration script for: ${topic}
Tone: ${tone}
Absurdity: ${chaos}/10
TARGET: 8-10 anchors covering this topic comprehensively at board-exam level. Do NOT omit any major category, step, or classification tier.

SETTING: Prefer an ORIGINAL setting name that is a clean phonetic pun or sound-alike for a key term in the topic. If that would be awkward, use a thematic setting whose spatial layout teaches the topic. Use hand-drawable materials (wood, brick, paper, chalkboard, fabric, stone, ceramic) — NOT modern clinical spaces.

MNEMONIC CHARACTERS are encouraged — figures whose names, shapes, or actions encode medical concepts. No tour-guide narrator character. The scene is a frozen static moment, not an animation.

For EVERY anchor, state the HOOK first (sound-alike, look-alike, functional, contrast, or spatial) and explain WHY the visual encodes the fact. The narrator points out elements in a STATIC IMAGE and explicitly states the mnemonic link.`;

  let storyData = null;
  let imagePromptText = '';

  try {
    const compactStorySystem = `You write original medical visual mnemonic memory-palace scripts for a single static illustration.

Return ONLY XML in this exact order: <scene_title>, <opening>, 8-10 repeated <vo_line> blocks, <review_script>.

Clinical accuracy and completeness are mandatory:
- For scoring systems, protocols, algorithms, and classifications, cover every major item in sequence.
- Group related sub-items into 8-10 anchors, but preserve every distinct number, range, angle, duration, threshold, and exception.
- Use the supplied clinical design context when present; it is the completeness checklist.

Visual mnemonic rules:
- Every anchor starts with HOOK: sound-alike, look-alike, functional, contrast, or spatial.
- Prefer silhouette-first objects/characters over text labels. Text may only be a short sound-alike NAME; NEVER draw numbers, doses, units, thresholds, or formulas — those exact values are spoken in NARRATION and recorded in ANCHOR, never printed in the image.
- VISUAL must be one compact physical drawing instruction, not a label list: one main object/character interaction, one location phrase, and at most one visible text surface (a name, never a number).
- Avoid the words labeled, reads, showing, shows, sign, chalkboard, ribbon, stamped, or plaque unless that single word describes the only text-bearing surface in the anchor.
- Avoid checklists, generic posters, ordinary clipboards, repeated same-shaped props, modern screens, glass, chrome, and medical equipment used literally.
- VISUAL is max 24 words. ANCHOR is max 30 words. NARRATION is 2-3 concise spoken sentences.
- No proprietary mnemonic scenes, characters, symbols, or layouts.

${clinicalContext}

Schema:
<vo_line>
HOOK: [strategy] - why the visual encodes the fact
NARRATION: [concise spoken explanation]
VISUAL: [drawn object/character, position, one short mnemonic NAME only if needed — never a number/dose/formula]
ANCHOR: [clinical fact only]
</vo_line>

<review_script>
One line per anchor: "When you see [image element] - remember [clinical fact]"
</review_script>`;

    const denseProtocol = isDenseProtocolTopic(topic, coreConcepts);
    const storyAttempts = [];
    const compactBody = (label, extraUser = '') => ({
      label,
      body: {
        model: CLAUDE_MODEL,
        max_tokens: 6144,
        system: compactStorySystem,
        messages: [{
          role: 'user',
          content: extraUser ? `${storyUser}\n\n${extraUser}` : storyUser
        }]
      }
    });
    if (!denseProtocol) {
      storyAttempts.push({
        label: 'advisor-full',
        body: withAdvisor({
          model: CLAUDE_MODEL,
          max_tokens: 8192,
          system: storySystem,
          messages: [{ role: 'user', content: storyUser }]
        })
      });
    }
    storyAttempts.push(compactBody(denseProtocol ? 'dense-compact' : 'timeout-compact-fallback'));
    storyAttempts.push(compactBody(
      denseProtocol ? 'dense-compact-strict' : 'timeout-compact-strict-fallback',
      'STRICT RETRY REQUIREMENT: The final output is invalid if it contains more than 10 <vo_line> blocks, any VISUAL over 30 words, arrow glyphs, speech bubbles, or more than one visible text surface in one anchor. Each VISUAL must be one compact drawing instruction: one object/character interaction plus one location phrase. Merge related sub-items until there are exactly 8-10 anchors. Do not omit facts; encode dense clinical facts with silhouette-first object interactions, scale, position, containment, blocking, and contrast. Use one short text label only when an essential number/formula cannot be encoded by shape.'
    ));
    storyAttempts.push(compactBody(
      denseProtocol ? 'dense-visual-hard-gate' : 'timeout-visual-hard-gate-fallback',
      'FINAL VISUAL HARD GATE: Rewrite the scene with 8-10 anchors and make every VISUAL pass these rules: 24 words or fewer; no arrow glyphs; no speech bubbles; no more than one quoted label per anchor; no more than one text-bearing object per anchor; no checklist ribbons, no logbook rows, no multi-label signs. Preserve all essential medical facts by moving details into NARRATION and ANCHOR, while the VISUAL uses one strong object interaction plus at most one precision plaque.'
    ));

    let storyValidation = null;
    let lastStoryError = null;

    for (let attemptIndex = 0; attemptIndex < storyAttempts.length; attemptIndex += 1) {
      const attempt = storyAttempts[attemptIndex];
      const requestBody = attempt.body;
      showDebug(`STORY REQUEST (${attempt.label})`, JSON.stringify({
        model: requestBody.model,
        advisor: !!requestBody.tools?.some(tool => tool?.name === 'advisor') ? CLAUDE_ADVISOR_MODEL : null,
        max_tokens: requestBody.max_tokens,
        system_length: requestBody.system.length,
        user_length: storyUser.length
      }));

      let res;
      try {
        res = await claudeFetch(requestBody, `stage2-story-script-${attempt.label}`);
      } catch(fetchErr) {
        lastStoryError = new Error(fetchErr.message || 'Could not reach the provider proxy.');
        if (attemptIndex < storyAttempts.length - 1) continue;
        throw lastStoryError;
      }

      const rawText = await res.text().catch(() => '(could not read body)');
      showDebug(`STORY RESPONSE (${attempt.label}) — HTTP ${res.status}`, rawText.slice(0, 2000));

      if (!res.ok) {
        lastStoryError = new Error(`Scene Narrative: HTTP ${res.status} — ${rawText.slice(0, 500)}`);
        if ((res.status === 504 || res.status === 502) && attemptIndex < storyAttempts.length - 1) continue;
        throw lastStoryError;
      }

      let raw;
      try {
        raw = JSON.parse(rawText);
      } catch(jsonErr) {
        lastStoryError = new Error(`JSON parse failed: ${jsonErr.message} — raw: ${rawText.slice(0, 300)}`);
        if (attemptIndex < storyAttempts.length - 1) continue;
        throw lastStoryError;
      }

      let txt = '';
      try {
        txt = parseAPIResponse(raw, 'Scene Narrative');
      } catch(parseErr) {
        lastStoryError = parseErr;
        if (raw?.stop_reason === 'max_tokens' && attemptIndex < storyAttempts.length - 1) continue;
        throw parseErr;
      }

      storyData = parseStoryXml(txt);
      storyValidation = validateStoryData(storyData);
      if (storyValidation.fatal.length) {
        showDebug(`STORY VALIDATION FAILED (${attempt.label})`, storyValidation);
        lastStoryError = new Error(`Scene Narrative validation failed: ${storyValidation.fatal.join(' ')}`);
        const retryableValidation = raw?.stop_reason === 'max_tokens'
          || storyValidation.fatal.some(message => /Too many anchors|visual|text surfaces|arrow glyphs|speech bubble/i.test(message));
        if (retryableValidation && attemptIndex < storyAttempts.length - 1) continue;
        if (retryableValidation) {
          // Iterative micro-repair. One pass frequently can't drag a stubborn
          // over-length VISUAL under the word cap, and a single leftover fatal must
          // not abort an otherwise-complete scene. Re-run the repair, feeding the
          // still-failing XML back, up to a small budget; once the only remaining
          // fatals are word-count overflows, switch to the focused length repair.
          const MAX_MICRO_REPAIRS = 3;
          let repairInput = txt;
          for (let repairPass = 0; repairPass < MAX_MICRO_REPAIRS; repairPass++) {
            const lengthOnly = storyValidation.fatal.every(m => /visual is \d+ words;/i.test(m));
            const repairedText = await repairStoryVisualFormat(repairInput, storyValidation, { lengthOnly });
            if (!repairedText) break;
            storyData = parseStoryXml(repairedText);
            storyValidation = validateStoryData(storyData);
            if (!storyValidation.fatal.length) {
              storyValidation.warnings.push(`Visual fields were micro-repaired after hard-gate validation (${repairPass + 1} pass${repairPass ? 'es' : ''}).`);
              break;
            }
            showDebug(`STORY VISUAL MICRO-REPAIR PASS ${repairPass + 1} STILL FAILING`, storyValidation);
            lastStoryError = new Error(`Scene Narrative validation failed after visual micro-repair: ${storyValidation.fatal.join(' ')}`);
            repairInput = repairedText;
          }
          if (!storyValidation.fatal.length) break;
        }
        throw lastStoryError;
      }

      if (raw?.stop_reason === 'max_tokens') {
        storyValidation.warnings.push('Provider stopped at max_tokens; review the rapid review script for completeness.');
      }
      break;
    }

    if (!storyData || !storyValidation) {
      throw lastStoryError || new Error('Scene Narrative: no usable story response.');
    }

    showBody('story');

    if (storyValidation.warnings.length) {
      showDebug('STORY VALIDATION WARNINGS', storyValidation.warnings);
    }

    renderStoryData(storyData);

    setStatus('story', '✓ Complete', 'done');
    const warningSuffix = storyValidation.warnings.length
      ? ` ${storyValidation.warnings.length} structure warning(s) need review.`
      : '';
    setStageDetail('story', `${storyData.voLines.length} anchors generated. Review the script, then save or repair if needed.${warningSuffix}`);
    // Grade the generation against the upstream anchor contract (blueprint MUST
    // categories ∪ Stage 1 core concepts), not against its own anchors.
    const anchorContract = window.MnemorizedLessonSpec?.buildAnchorContract
      ? window.MnemorizedLessonSpec.buildAnchorContract(lessonSpec, coreConcepts)
      : coreConcepts;
    await runMedicalQualityGate(storyData, anchorContract);
  } catch(e) {
    const box = document.getElementById('debug-box');
    const prev = box.textContent;
    box.style.display = 'block';
    box.textContent = `── STORY ERROR ──\n${e.message}\n\n── Previous debug output ──\n${prev}`;
    setStatus('story', '✗ ' + e.message.slice(0, 80), 'error');
    setStageDetail('story', 'Scene generation stopped before a usable script was created.');
    btn.disabled = false; btn.innerHTML = '✦ FORGE PALACE';
    return;
  }

  // ── STAGE 3: Image prompts ────────────────────────
  setStatus('prompt', '✦ Building image prompts…', 'running');
  setStageDetail('prompt', 'Preparing constitution-guided illustration prompts from the generated anchor script.');

  try {
    const n = storyData.voLines.length;
    const pair = await buildImagePromptPair(
      topic,
      storyData,
      'initial',
      'stage3-gemini-prompt-director',
      'stage3-image-prompt'
    );
    renderImagePromptPair(
      storyData,
      pair,
      '✓ Image prompts ready',
      `Illustration handoff ready with ${n} anchors using ${pair.director === 'gemini' ? 'Gemini constitution director' : 'fallback prompt composer'}.`
    );

  } catch(e) {
    setStatus('prompt', `✦ PROMPT ERROR ── ${e.message}`, 'error');
    setStageDetail('prompt', 'The palace script is still available, but image prompts failed to build.');
    console.error('Image prompt error:', e);
    setCurrentPalaceData(storyData, '', '');
    btn.disabled = false;
    btn.innerHTML = '✦ FORGE PALACE';
    return;
  }

  // ── STAGE 4: Explicit image generation ──────────
  setStageDetail('prompt', 'Image prompts are ready. Use Generate Images when you want to spend an image request, or export the bundle for Gemini web QA.');

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
