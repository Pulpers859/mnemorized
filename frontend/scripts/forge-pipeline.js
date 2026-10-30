// ══════════════════════════════════════════════════
// FORGE PIPELINE — constants, config UI, main pipeline
// Depends on: forge-state.js, forge-auth.js, forge-upload.js
// ══════════════════════════════════════════════════

// ── Shared constants ─────────────────────────────────────────────

let forgeOperation = 0;
let imageRequest = 0;
window.MnemorizedForgeOperations = {current: () => forgeOperation, cancel() {
  forgeOperation++;
  window.MnemorizedVisualPreflight?.reset();
  const button = document.getElementById('forge-btn');
  if (button) { button.disabled = false; button.innerHTML = '✦ FORGE PALACE'; }
}};

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

const NO_PRECISION_TEXT_RULE = 'PRECISION VALUES LIVE ONLY IN NARRATION AND FLASHCARDS. Surfaces stay blank except for source-required mnemonic names on their own objects. ' +
  'Encode thresholds as objects crossing a physical boundary, relative values as obvious size contrast, and small counts as oversized countable objects (at most five). ' +
  'Time cues use an unmarked hourglass. Clock faces, dials, gauges, and requested hand positions are replaced by these shape-first interactions. ' +
  'The illustration contains mnemonic shapes and actions while exact numbers, doses, units, lab values, percentages, and formulas remain spoken study facts.';

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
  'Speed/timing: turtle or snail = slow/careful correction; rabbit = fast/urgent; unmarked hourglass = time window; repeated sunrise/sunset objects = day sequence; metronome = rate/rhythm. Clock faces, stopwatch readings, and exact hand positions are not render-safe precision devices.',
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
const IMAGE_PROMPT_MAX_WORDS = 600;

function requestedAnchorCount(topic) {
  const match = String(topic || '').match(/(?<![\d-])\b(eight|nine|ten|8|9|10)\s+anchors\b/i);
  return match ? ({eight: 8, nine: 9, ten: 10}[match[1].toLowerCase()] || Number(match[1])) : null;
}

function validateRequestedStory(story, count) {
  const result = validateStoryData(story);
  if (count && story?.voLines?.length !== count) result.fatal.push(`Requested exactly ${count} anchors; returned ${story?.voLines?.length || 0}. Preserve all teaching units while grouping them into the requested count.`);
  result.all = result.fatal.concat(result.warnings);
  return result;
}

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
  // Whitespace cleanup only: shortening a visual can delete its load-bearing cue.
  return String(visual || '').replace(/\s+/g, ' ').trim();
}

function trimWords(text, maxWords) {
  const words = String(text || '').trim().split(/\s+/).filter(Boolean);
  if (words.length <= maxWords) return words.join(' ');
  return words.slice(0, maxWords).join(' ') + '...';
}

// Quoted precision text belongs in narration/cards, not on the drawn object.
function isPrecisionLabel(text) {
  return /[0-9=×+±<>≤≥÷%/]|\b(?:mL|kg|mg|mcg|mmol|mEq|mOsm|bpm|hr|min)\b/i.test(text);
}

function stripPrecisionTokens(text) {
  return String(text || '')
    .replace(/\b(?:reads?|reading|labell?ed|marked|stamped|shows?|says?|displays?|engraved|etched|inscribed|printed)\s+["“”]([^"“”\n]+)["“”]/gi,
      (m, tok) => (isPrecisionLabel(tok) ? '' : m))
    .replace(/["“”]([^"“”\n]+)["“”]/g, (m, tok) => (isPrecisionLabel(tok) ? '' : m))
    .replace(/\s{2,}/g, ' ').replace(/\s+([.,;])/g, '$1').trim();
}

function imageAnchorVisual(anchor, index) {
  const visual = stripPrecisionTokens(condenseForImage(anchor.visual))
    .replace(/\bfigure-8(?=\s+(?:knot|loop)\b)/gi, (notation, offset, source) => {
      const written = /\b(?:reads?|reading|labell?ed|marked|stamped|says?|displays?|engraved|etched|inscribed|printed|written|text|caption)\b[^.;]*$/i.test(source.slice(0, offset));
      return written ? notation : 'figure-eight';
    })
    .replace(/[.\s]+$/, '').trim();
  if (!visual) throw new Error(`Image anchor ${index + 1} has no drawable visual. Repair it through Forge.`);
  // Do not guess how to translate a precision value into a new clinical hook.
  if (/[0-9↑↓=<>≤≥%]/.test(visual)) {
    throw new Error(`Image anchor ${index + 1} still contains numeric or symbolic instructions. Repair its VISUAL through Forge; keep exact values in narration and cards.`);
  }
  return visual;
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
function buildImageAnchorLines(anchors) {
  if (!anchors.length) throw new Error('Image prompts require the complete Forge anchor list.');
  return anchors.map((v, index) => {
    const visual = imageAnchorVisual(v, index);
    const lead = zoneLeadIn(v.zone);
    const alreadyPlaced = /^(?:indoors\b|outdoors\b|upstage\b|downstage\b|stage-)/i.test(visual) ||
      /\b(?:(?:on|at|in|against|just|directly|off|toward|above|below|behind|beside|near|far|left|right|center|along|by|from)\s+(?:(?:the|a|an)\s+)?(?:(?:far|back|front|left|right|center|middle|near|side)\s+)*(?:wall|floor|ceiling|corner|doorway|alcove|room|corridor|foreground|background|stage)|(?:mid|middle|center|centre)[ -]+corridor|floor[ -]+(?:center|centre|left|right)|foreground|background)\b/i.test(visual);
    if (lead && !alreadyPlaced) {
      return `${lead}, ${visual.charAt(0).toLowerCase()}${visual.slice(1)}.`;
    }
    return `${visual}.`;
  }).join(' ');
}

// A quoted word is not automatically a mnemonic name. Require source naming or
// phonetic-hook evidence; ambiguous text needs a Forge repair, not an invented hook.
function extractRenderableLabels(anchors) {
  const precision = [];
  const ordinary = [];
  const seen = new Set();
  (anchors || []).forEach((v, index) => {
    const src = String(v.visual || '');
    const re = /["“”]([^"“”\n]+)["“”]/g;
    let m;
    while ((m = re.exec(src)) !== null) {
      const tok = m[1].trim();
      if (!tok) continue;
      const isPrecision = isPrecisionLabel(tok);
      const nameHook = /\b(?:sound[- ]alike|phonetic|mnemonic name|acronym)\b/i.test(v.hook || '');
      const explicitlyNamed = /\b(?:named|called|name(?:d)?\s+(?:tag|label)\s+(?:reads?|says?))\s*$/i.test(src.slice(0, m.index));
      if (!isPrecision && (!/^[\p{L}][\p{L} '\-]*$/u.test(tok) || tok.split(/\s+/).length > 3 || !(nameHook || explicitlyNamed))) {
        throw new Error(`Image anchor ${index + 1} has text that is not an explicit short mnemonic name. Repair its VISUAL through Forge.`);
      }
      const key = tok;
      if (seen.has(key)) continue;
      seen.add(key);
      (isPrecision ? precision : ordinary).push(tok);
    }
  });
  return { precision, ordinary };
}

// Keep this marker for the image-audit repair inserter. The fence is always last.
function buildTextAllowlistFence(anchors) {
  const { ordinary } = extractRenderableLabels(anchors);
  return 'RENDERABLE TEXT ALLOWLIST: ' + (ordinary.length
    ? `Only these source-required mnemonic names appear, spelled exactly on their own objects: ${ordinary.join(', ')}. All other surfaces and empty space stay blank and unmarked.`
    : 'Every surface and all empty space stay blank and unmarked; the entire illustration is text-free.');
}

// Guarantee the deterministic fence is the last thing in a prompt no matter which
// builder authored the body (local composer, Claude fallback, or the server-side
// Gemini prompt director). Replace stale or incomplete fences instead of trusting
// the mere presence of the marker.
function ensureTextAllowlistFence(prompt, anchors) {
  const text = String(prompt || '').split('RENDERABLE TEXT ALLOWLIST')[0].trim();
  return text + '\n\n' + buildTextAllowlistFence(anchors);
}

function composeImagePrompt2(sceneDesc, assigned) {
  return 'Hand-drawn flat marker cartoon, wide 16:9 single coherent scene, varied ink outlines, vivid contrasting colors and even lighting. ' +
    'Grounded objects, uncluttered spatial hierarchy. Every described interaction appears once with distinct silhouettes.\n\n' +
    condenseForImage(sceneDesc) + '\n\n' + buildImageAnchorLines(assigned) + '\n\n' +
    'Shapes and interactions carry hooks; exact values stay in narration and cards.\n\n' +
    buildTextAllowlistFence(assigned);
}

function clampImagePrompt(prompt, maxChars = IMAGE_PROMPT_MAX_CHARS) {
  const text = String(prompt || '').trim();
  if (text.length > maxChars) {
    throw new Error('Image prompt exceeds the character budget. Rebuild through Forge; anchors and the text allowlist cannot be truncated.');
  }
  return text;
}

function normalizeImagePromptPair(pair, assigned) {
  let normalized = { ...pair };
  if (assigned) {
    normalized.prompt2 = ensureTextAllowlistFence(normalized.prompt2, assigned);
    const body = condenseForImage(normalized.prompt2).toLowerCase();
    const missingVisual = assigned.some((v, index) => !body.includes(imageAnchorVisual(v, index).toLowerCase()));
    if (missingVisual || normalized.prompt1.length > IMAGE_PROMPT_MAX_CHARS ||
        normalized.prompt2.length > IMAGE_PROMPT_MAX_CHARS ||
        normalized.prompt2.split(/\s+/).length > IMAGE_PROMPT_MAX_WORDS) {
      // Provider paraphrases cannot prove full source coverage. Recompose from
      // every original visual rather than trusting a partial or oversized body.
      normalized = { ...normalized, ...composeImagePromptPair(normalized.scene_description, assigned) };
    }
  }
  if (String(normalized.prompt2 || '').trim().split(/\s+/).length > IMAGE_PROMPT_MAX_WORDS) {
    throw new Error('Full-scene image prompt exceeds 600 words with all anchors intact. Repair the source VISUAL fields through Forge; no anchors were dropped.');
  }
  return {
    ...normalized,
    prompt1: clampImagePrompt(normalized.prompt1),
    prompt2: clampImagePrompt(normalized.prompt2),
  };
}

function composeImagePromptPair(sceneDesc, assigned) {
  const room = condenseForImage(sceneDesc);
  const prompt1 = 'Hand-drawn flat marker cartoon, wide 16:9 empty room foundation. Bare architecture, blank unmarked surfaces and open floor space. ' + room;
  const prompt2 = composeImagePrompt2(room, assigned);
  return normalizeImagePromptPair({ prompt1, prompt2, scene_description: room, director: 'local' });
}

async function buildClaudeImagePromptPair(topic, storyData, assigned, stage) {
  const n = assigned.length;
  const ipSystem = 'You write scene descriptions for Gemini image generation. ' +
    'Output ONLY the spatial layout and atmosphere — surfaces, materials, lighting, camera angle. ' +
    'Dense, comma-separated descriptive phrases. Do NOT include any style instructions or rendering directives. ' +
    'CRITICAL: Describe architecture only: one continuous room with an open, undivided floor, walls, ceiling, doorways and windows. Target 20-35 words; always use fewer than 60 words. Keep architectural detail minimal. ' +
    'No divided bays, booths, panels, grids, painted zone lines, checklist walls or numbered stations. ' +
    'Do NOT invent or list anchor props, furniture, tools, people or characters. ' +
    'The anchor objects are added separately — your job is ONLY the empty room that they will be placed into. ' +
    'Design the room as a clear spatial memory map using natural depth and open space, not drawn boundaries or compartments.';

  const p1UserMsg = `Write a scene description for a memory palace illustration. Output ONLY the scene/room — no objects, no style directives.

MEDICAL TOPIC: ${topic}
SCENE TITLE: ${storyData.scene_title}
ATMOSPHERE: ${storyData.opening}
TOTAL ANCHORS TO FIT: ${n}

Requirements:
- 20-35 words — minimal architecture ONLY; always fewer than 60 words
- One continuous room with an open, undivided floor; describe only walls, floor, ceiling, doorways, windows and their materials
- No divided bays, booths, panels, grids, painted zone lines, checklist walls or numbered stations
- Do NOT name any specific objects, furniture, or tools — those are added separately as medical anchors
- Flat-friendly materials: wood, paper, brick, chalkboard, cork, cardboard, fabric, stone, ceramic — NO glass, chrome, screens, or modern clinical equipment
- NO people or characters
- Wide establishing shot, aspect ratio 16:9, spacious enough for ${n} future anchors within the same continuous space; their positions come from the supplied visuals, not invented partitions`;

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
  }, assigned);
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

async function prepareImagePromptPair(topic, storyData, options = {}) {
  if (!window.MnemorizedVisualPreflight) throw new Error('Visual preflight module did not load. Refresh Forge.');
  const operation = forgeOperation;
  const originalKey = JSON.stringify(storyData);
  const isCurrent = () => operation === forgeOperation &&
    document.getElementById('topic').value.trim() === topic && JSON.stringify(storyData) === originalKey &&
    (typeof options.isCurrent !== 'function' || options.isCurrent());
  const prepared = await window.MnemorizedVisualPreflight.prepare(topic, storyData, currentQualityGateData,
    {...options, isCurrent});
  if (operation !== forgeOperation) throw new Error('Preflight operation superseded.');
  if (document.getElementById('topic').value.trim() !== topic || JSON.stringify(storyData) !== originalKey) {
    window.MnemorizedVisualPreflight.reset();
    throw new Error('Lesson changed during preflight. Rebuild the current lesson.');
  }
  // Compile only reviewed source text: a second director must not add new props,
  // contradictory staging, or paraphrase away a required relationship.
  const pair = composeImagePromptPair(prepared.story.opening, assignZones(prepared.story.voLines));
  pair.director = 'reviewed-deterministic';
  pair.story = prepared.story;
  await window.MnemorizedVisualPreflight.bind(topic, prepared.story, pair);
  if (operation !== forgeOperation) throw new Error('Preflight operation superseded.');
  if (!isCurrent()) {
    window.MnemorizedVisualPreflight.reset();
    throw new Error('Lesson changed during prompt binding. Rebuild the current lesson.');
  }
  return pair;
}

function renderImagePromptPair(storyData, pair, doneStatus, detail) {
  storyData = pair.story || storyData;
  renderStoryData(storyData);
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

function invalidateImagePrompts() {
  window.MnemorizedVisualPreflight?.invalidate();
  currentPromptData = { prompt1: '', prompt2: '' };
  ['img-prompt-1', 'img-prompt-2'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = '';
  });
  ['prompt-copy-1', 'prompt-copy-2'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  delete window.__mnemorizedAntigravityPrompts;
  const generateButton = document.getElementById('generate-images-btn');
  if (generateButton) { generateButton.disabled = false; generateButton.innerHTML = 'Generate Images'; }
  ['gen-img-1-el', 'gen-img-2-el', 'gen-img-result-el'].forEach(id => {
    document.getElementById(id)?.removeAttribute('src');
  });
}

// Validate length before spending a request. Only surrounding whitespace may
// be trimmed; anchor content and the allowlist must never be truncated.
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
  const request = ++imageRequest;
  const operation = forgeOperation;
  const topic = document.getElementById('topic')?.value?.trim() || '';
  const storyKey = JSON.stringify(currentStoryData);
  const rawPrompts = [document.getElementById('prompt-copy-1')?.value?.trim(), document.getElementById('prompt-copy-2')?.value?.trim()];
  const active = () => request === imageRequest && operation === forgeOperation &&
    topic === (document.getElementById('topic')?.value?.trim() || '') && storyKey === JSON.stringify(currentStoryData) &&
    rawPrompts.every((value, i) => value === document.getElementById(`prompt-copy-${i + 1}`)?.value?.trim());
  let gate;
  try {
    gate = gateImagePrompts(
      document.getElementById('prompt-copy-1')?.value,
      document.getElementById('prompt-copy-2')?.value
    );
    if (!window.MnemorizedVisualPreflight) throw new Error('Visual preflight module did not load. Refresh Forge.');
    window.MnemorizedVisualPreflight.requireEvidence(currentStoryData, currentQualityGateData);
    window.MnemorizedVisualPreflight.assertReady(
      document.getElementById('topic')?.value?.trim() || '', currentStoryData,
      document.getElementById('prompt-copy-1')?.value, document.getElementById('prompt-copy-2')?.value
    );
  } catch (error) {
    delete window.__mnemorizedAntigravityPrompts;
    setStatus('prompt', 'Image prompt validation blocked', 'error');
    setStageDetail('prompt', error.message);
    showBody('prompt');
    const status = document.getElementById('gen-img-status');
    if (status) status.textContent = error.message;
    const btn = document.getElementById('generate-images-btn');
    if (btn) { btn.disabled = false; btn.innerHTML = '✦ Generate Images'; }
    return;
  }
  try {
    const p1 = gate.p1;
    const p2 = gate.p2;
    if (!p1 && !p2) { alert('Forge a palace first to generate image prompts.'); return; }
    if (gate.trimmed) {
      // Persist the clamped versions so what we send matches what the user sees and
      // copies. (setStageDetail below is overwritten immediately, so note it on the
      // durable prompt panels instead.)
      if (p1) { document.getElementById('prompt-copy-1').value = p1; document.getElementById('img-prompt-1').textContent = p1; }
      if (p2) { document.getElementById('prompt-copy-2').value = p2; document.getElementById('img-prompt-2').textContent = p2; }
      console.info('[Mnemorized] Surrounding image-prompt whitespace was removed before generation.');
    }

    // Render-target fork: Antigravity mode never calls the Gemini API. Branch before
    // the backend/Gemini readiness checks so a billing-blocked or unconfigured Gemini
    // key does not stop an Antigravity render.
    if (document.getElementById('image-target-antigravity')?.checked) {
      const btn = document.getElementById('generate-images-btn');
      if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Staging…'; }
      handoffToAntigravity([p2]);
      return;
    }

    if (window.MnemorizedFirstAttempt?.isActive()) {
      throw new Error('First-attempt images must use the frozen Antigravity handoff, not the Gemini API lane.');
    }

    if (forgeReplayMode !== 'replay') {
      if (!backendState.checked) await refreshBackendStatus();
      if (!active()) return;
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

    const prompts = [p2];

    // Force-refresh the token — the pipeline may have run for minutes and the JWT expired
    if (typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
      try {
        const { data: refreshed } = await supabaseClient.auth.refreshSession();
        if (!active()) return;
        if (refreshed?.session) {
          authState.session = refreshed.session;
        }
      } catch (_) { /* best-effort — the 401 retry below will catch it */ }
    }
    if (!active()) return;

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
        if (!active()) throw fetchErr;
        backendState.reachable = false;
        setBackendBadge('offline', '⚠ PROXY OFFLINE');
        throw new Error(`Proxy unavailable: ${fetchErr.message}`);
      }
      if (!active()) throw new Error('Image request superseded.');

      // 401 → refresh token and retry once
      if (res.status === 401 && typeof supabaseClient !== 'undefined' && supabaseClient?.auth) {
        const { data: refreshData } = await supabaseClient.auth.refreshSession();
        if (!active()) throw new Error('Image request superseded.');
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
      if (!active()) throw new Error('Image request superseded.');

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
        if (!active()) return;
        if (res.ok || !TRANSIENT_CODES.has(res.status) || attempt === MAX_RETRIES) break;
        if (status) status.textContent = 'Gemini hiccup — retrying…';
        await new Promise(r => setTimeout(r, 2000 * (attempt + 1)));
        if (!active()) return;
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
      if (!active()) return;
      const images = data.images || [];
      const promptErrors = data.prompt_errors || [];

      images.forEach((img, i) => {
        const n = images.length === 1 ? 2 : i + 1;
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
      if (!active()) return;
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
  } catch (error) {
    if (active()) throw error;
  } finally {
    if (request === imageRequest && operation === forgeOperation && !active()) {
      const button = document.getElementById('generate-images-btn');
      if (button) button.disabled = false;
      setStatus('prompt', 'Image request discarded', 'error');
      setStageDetail('prompt', 'The lesson or prompts changed during generation. Rebuild before rendering again.');
    }
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
    first_attempt_profile: window.MnemorizedFirstAttempt?.snapshot() || null,
    anti_meta_text: ANTI_META_TEXT,
    story: currentStoryData || null,
    image_prompts: {
      prompt1: document.getElementById('prompt-copy-1')?.value || '',
      prompt2: document.getElementById('prompt-copy-2')?.value || '',
    },
    quality_gate: qualitySummary,
    quality_gate_data: currentQualityGateData || null,
    visual_preflight: window.MnemorizedVisualPreflight?.getReport() || null,
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

async function rebuildImagePromptsForStory(storyData, operationToken = null, options = {}) {
  if (!storyData?.voLines?.length) {
    setStatus('prompt', 'No repaired story', 'error');
    setStageDetail('prompt', 'Image prompts could not be rebuilt because the repaired script has no anchors.');
    return;
  }

  const topic = document.getElementById('topic')?.value?.trim() || 'medical topic';
  const operation = operationToken ?? ++forgeOperation;
  if (operation !== forgeOperation) return;
  const active = () => operation === forgeOperation && topic === document.getElementById('topic').value.trim();
  const n = storyData.voLines.length;

  setStatus('prompt', 'Rebuilding image prompts...', 'running');
  setStageDetail('prompt', 'Rebuilding constitution-guided illustration prompts from the repaired anchor script.');

  try {
    const pair = await prepareImagePromptPair(topic, storyData, options);
    if (!active()) return;
    renderImagePromptPair(
      storyData,
      pair,
      '✓ Rebuilt from repaired script',
      `All ${n} anchors passed pre-render risk review. Pixel quality remains unverified until an independent image audit.`
    );
  } catch (error) {
    if (!active()) return;
    invalidateImagePrompts();
    setCurrentPalaceData(storyData, '', '');
    setStatus('prompt', `Prompt rebuild failed: ${error.message}`, 'error');
    showBody('prompt');
    if (currentQualityGateData) renderQualityGateResult(currentQualityGateData);
    setStageDetail('prompt', 'The repaired script was kept, but image prompts must be rebuilt before generating — click Forge again or re-run the prompt step.');
  }
}

async function repairStoryVisualFormat(xmlText, validation, options = {}) {
  const errors = (validation?.fatal || []).join('\n- ');
  if (!xmlText || !errors) return '';
  const active = () => options.operation === forgeOperation &&
    options.topic === document.getElementById('topic').value.trim();
  if (!active()) return '';
  const before = options.originalStory || parseStoryXml(xmlText);
  if (!before.voLines?.length || !window.MnemorizedStoryContract.preservesLearningText(before, parseStoryXml(xmlText))) {
    throw new Error('Scene format repair requires a complete, lossless original lesson.');
  }
  // When the only remaining fatals are VISUALs over the hard word cap, escalate to
  // a focused length-repair: a general repair pass often leaves a dense anchor one
  // or two words over, and a single word-count fatal must not abort a complete scene.
  const lengthDirective = options.lengthOnly
    ? `\n\nCRITICAL LENGTH REPAIR: Compress ONLY the named over-length VISUAL fields toward ${window.MnemorizedStoryContract.limits.visualTarget} words (maximum ${window.MnemorizedStoryContract.limits.visualMax}). Preserve all cue identities and load-bearing relationships. Every other field, including all learning text, stays byte-for-byte unchanged. If that is impossible, return the original unchanged; do not delete or relocate teaching content.`
    : '';
  const body = {
    model: CLAUDE_MODEL,
    max_tokens: 6144,
    system: `You repair XML medical memory-palace scripts for visual format only.

Return ONLY the full corrected XML. Preserve scene_title, opening, anchor count/order, HOOK, NARRATION, ANCHOR, and review_script byte-for-byte.

Only rewrite VISUAL fields. Do not change cue identities or learning text. A different association requires full Forge redesign, not format repair.
Rules for every VISUAL:
- Target ${window.MnemorizedStoryContract.limits.visualTarget} words, maximum ${window.MnemorizedStoryContract.limits.visualMax}.
- One compact physical drawing instruction.
- One main object or character interaction plus one location phrase.
- No arrow glyphs, speech bubbles, checklist rows, multi-label signs, or more than one text-bearing surface.
- Replace exact-value clock faces, clock hands, stopwatches, dials, gauges, and precision plaques with an unmarked physical threshold, obvious size contrast, or at most five countable objects.
- Preserve every load-bearing relationship. Do not move content into NARRATION or ANCHOR or delete clinical facts.`,
    messages: [{
      role: 'user',
      content: `Fix these validation errors:\n- ${errors}${lengthDirective}\n\nOriginal XML:\n${xmlText}`
    }]
  };
  const res = await claudeFetch(body, 'stage2-story-visual-micro-repair', options.evidenceAvailable ? {
    'x-evidence-grounding': 'true',
    'x-evidence-topic': encodeHeaderValue(options.topic),
    'x-visual-preflight': 'true',
  } : {});
  const rawText = await res.text().catch(() => '(could not read body)');
  if (!active()) return '';
  const box = document.getElementById('debug-box');
  if (box) {
    box.style.display = 'block';
    box.textContent = `── STORY VISUAL MICRO-REPAIR — HTTP ${res.status} ──\n${rawText.slice(0, 2000)}`;
  }
  if (!res.ok) return '';
  const raw = JSON.parse(rawText);
  if (raw.stop_reason !== 'end_turn') throw new Error('Scene format repair did not finish; no partial lesson was accepted.');
  const repaired = parseProviderContent(raw, 'Scene Narrative visual micro-repair');
  if (!window.MnemorizedStoryContract.preservesLearningText(before, parseStoryXml(repaired))) {
    throw new Error('Scene format repair changed protected learning text, room architecture or anchor inventory.');
  }
  return repaired;
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
  const operation = ++forgeOperation;
  const currentRun = () => operation === forgeOperation && topic === document.getElementById('topic').value.trim();
  window.MnemorizedVisualPreflight?.reset();
  invalidateImagePrompts();
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

  try {

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
    if (!currentRun()) return;

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
    if (!currentRun()) return;
    setStatus('quality', 'Demo skipped', 'done');
    setStageDetail('quality', 'Demo mode skips private medical retrieval and provider calls.');
    renderQualityGateMessage('Demo mode uses built-in sample content, so private medical retrieval is skipped.', 'success');
    await demoDelay(400);
    if (!currentRun()) return;

    setStatus('prompt', '✦ Building image prompts…', 'running');
    setStageDetail('prompt', 'Preparing illustration handoff prompts from the sample scene.');
    await demoDelay(1200);
    if (!currentRun()) return;

    const n = D.voLines.length;
    const assigned = assignZones(D.voLines);
    let demoP1;
    let demoP2;
    try {
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

      demoP1 = clampImagePrompt(demoP1Raw);
      demoP2 = clampImagePrompt(demoP2Raw);
    } catch (error) {
      invalidateImagePrompts();
      setCurrentPalaceData({
        scene_title: D.scene_title, opening: D.opening,
        voLines: D.voLines, review_script: D.review_script
      }, '', '');
      showBody('prompt');
      setStatus('prompt', 'Demo prompt validation blocked', 'error');
      setStageDetail('prompt', `The unchanged demo script is available for review, but its image prompt failed validation: ${error.message}`);
      btn.disabled = false;
      btn.innerHTML = '✦ FORGE PALACE';
      return;
    }

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
  if (window.MnemorizedFirstAttempt?.isActive() && (!evidenceAvailable || requestedAnchorCount(topic) !== 8)) {
    window.MnemorizedFirstAttempt.fail();
    setStatus('story', 'First-attempt source/scope contract blocked', 'error');
    setStageDetail('story', 'This profile requires source retrieval and exactly eight requested anchors.');
    return;
  }
  if (evidenceAvailable) {
    setStatus('story', '✦ Retrieving source evidence…', 'running');
    setStageDetail('story', 'Searching private medical knowledge base before generating concepts.');
  } else {
    setStatus('story', '✦ Analyzing topic…', 'running');
    setStageDetail('story', 'Extracting source-grounded clinical teaching units.');
  }
  let clinicalContext = '';
  let coreConcepts = [];
  const evidenceHeaders = evidenceAvailable ? {
    'x-evidence-grounding': 'true',
    'x-evidence-topic': encodeHeaderValue(topic),
  } : {};
  try {
    const ctxRes = await claudeFetch({
        model: CLAUDE_MODEL,
        max_tokens: 2600,
        system: `You are a senior clinical educator and board exam question writer designing original visual mnemonic memory scenes. Extract the essential teaching points for the requested learner and lesson scope. Prioritize recognition, decisions, and safety pitfalls. Cover the requested scope comprehensively without expanding an introductory lesson into an entire chapter.

COMPLETENESS CHECK: Before finalizing, verify the relevant categories within the requested scope. For example:
- For scoring systems: every sub-item and its specific scoring range
- For interpretation algorithms: every step in the systematic approach
- For drug classes: mechanism, indications, contraindications, key side effects, monitoring
- For pathophysiology: etiology, pathogenesis, clinical features, diagnosis, management, complications
- For procedures/protocols: indications, contraindications, steps, complications, alternatives

When SOURCE EVIDENCE is provided below, derive your core concepts from that material. Preserve its terminology, qualifiers, thresholds, and clinical details. Identify any missing source coverage explicitly instead of supplying facts from memory.
${lessonBlueprintText ? `\n${lessonBlueprintText}\n\nStay inside this blueprint's scope: cover every MUST category, and do NOT expand into the out-of-scope areas unless the topic clearly demands it.\n` : ''}
This step defines clinical coverage ONLY. Do not design a room, invent mnemonic objects, prescribe labels, or suggest clocks/dials/poses. The scene writer handles visual associations separately.
Output ONLY this XML tag, nothing else:

<core_concepts>Use the requested anchor count when specified, otherwise 8-12 concise teaching units. One per line, at most 45 words each. Cover essential recognition, diagnostic pitfalls, immediate treatment, escalation, and disposition when relevant. Each unit teaches one coherent decision or relationship. Preserve source qualifiers, uncertainty, ranges, and thresholds exactly; do not turn approximate evidence into false precision. Omit out-of-scope molecular detail and epidemiology. Do not omit essential safety steps.</core_concepts>
`,
        messages: [{ role: 'user', content: `Clinical topic: ${topic}\nLearner: ${lessonSpec?.learner || 'Use the learner level in the clinical topic; otherwise medical student'} — needs precise, high-yield anchors.` }]
      }, 'stage1-clinical-context', evidenceHeaders);
    if (!currentRun()) return;
    setStatus('story', '✦ Analyzing topic…', 'running');
    setStageDetail('story', 'Extracting source-grounded clinical teaching units.');
    const ctxRaw = await ctxRes.json();
    if (!currentRun()) return;
    if (!ctxRes.ok || ctxRaw.stop_reason === 'max_tokens') {
      throw new Error(ctxRaw.error?.message || 'Clinical planning did not finish. Retry the lesson before creating its scene.');
    }
    const ctxTxt = parseProviderContent(ctxRaw, 'Clinical Context');
    const core   = extractXmlTag(ctxTxt, 'core_concepts');
    if (!core) throw new Error('Clinical planning returned an incomplete fact map. Retry the lesson.');
    if (core) {
      coreConcepts = core.split('\n').map(l => l.replace(/^[-•*\d.)\s]+/, '').trim()).filter(Boolean);
      if (evidenceAvailable) {
        setStageDetail('story', 'Independently reviewing the clinical coverage contract against source evidence.');
        coreConcepts = await reviewMedicalCoverageContract(topic, coreConcepts);
        if (!currentRun()) return;
      }
      const blueprintSuffix = lessonBlueprintText ? `\n\n${lessonBlueprintText}` : '';
      clinicalContext = `SOURCE-GROUNDED CLINICAL COVERAGE:\n${coreConcepts.join('\n')}\n\nEvery anchor must encode a specific teaching unit above. Invent visual associations only in this scene-writing step; no upstream room plan is authoritative.${blueprintSuffix}`;
    }
  } catch(e) {
    if (!currentRun()) return;
    console.warn('Clinical context extraction failed:', e.message);
    window.MnemorizedFirstAttempt?.fail();
    setStatus('story', '✗ Clinical planning failed', 'error');
    setStageDetail('story', e.message);
    showDebug('CLINICAL PLANNING ERROR', e.message);
    btn.disabled = false;
    btn.innerHTML = '✦ FORGE PALACE';
    return;
  }

  // ── STAGE 2: Voiceover Script ─────────────────────
  if (!currentRun()) return;
  setStatus('story', '✦ Writing scene…', 'running');
  setStageDetail('story', 'Writing narration, visual anchors, encoded facts, and the rapid review script.');


  const storyUser = `Create an original visual mnemonic memory palace narration script for: ${topic}
Tone: ${tone}
Absurdity: ${chaos}/10
TARGET: Respect the requested learner, scope, and anchor count. Otherwise use 8-10 anchors. Cover the essential decisions and safety pitfalls within that scope.

SETTING: Prefer an ORIGINAL setting name that is a clean phonetic pun or sound-alike for a key term in the topic. If that would be awkward, use a thematic setting whose spatial layout teaches the topic. Use hand-drawable materials (wood, brick, paper, chalkboard, fabric, stone, ceramic) — NOT modern clinical spaces.

MNEMONIC CHARACTERS are encouraged — figures whose names, shapes, or actions encode medical concepts. No tour-guide narrator character. The scene is a frozen static moment, not an animation.

For EVERY anchor, state the HOOK first (sound-alike, look-alike, functional, contrast, or spatial) and explain WHY the visual encodes the fact. The narrator points out elements in a STATIC IMAGE and explicitly states the mnemonic link.`;

  let storyData = null;
  let imagePromptText = '';

  try {
    const compactStorySystem = `You write original medical visual mnemonic memory-palace scripts for a single static illustration.

Return only the required submit_memory_palace tool. Fill every one of its ${requestedAnchorCount(topic) || 8} ordered anchor slots. Each slot supplies its own hook, narration, visual, clinical anchor and rapid-review line. No XML or additional prose.

Clinical accuracy and completeness are mandatory:
- For scoring systems, protocols, algorithms, and classifications, cover every major item in sequence.
- Group related sub-items into 8-10 anchors, but preserve every distinct number, range, angle, duration, threshold, and exception.
- Use the supplied clinical design context when present; it is the completeness checklist.

Visual mnemonic rules:
- Every anchor starts with HOOK: sound-alike, look-alike, functional, contrast, or spatial.
- Prefer silhouette-first objects/characters over text labels. Text may only be a short sound-alike NAME; NEVER draw numbers, doses, units, thresholds, or formulas — those exact values are spoken in NARRATION and recorded in ANCHOR, never printed in the image.
- Never encode an exact value with a clock face, clock hands, stopwatch reading, dial, or gauge. Use an unmarked physical threshold, size contrast, or at most five countable oversized objects.
- VISUAL must be one compact physical drawing instruction, not a label list: one main object/character interaction, one location phrase, and at most one visible text surface (a name, never a number).
- Avoid the words labeled, reads, showing, shows, sign, chalkboard, ribbon, stamped, or plaque unless that single word describes the only text-bearing surface in the anchor.
- Avoid checklists, generic posters, ordinary clipboards, repeated same-shaped props, modern screens, glass, chrome, and medical equipment used literally.
- VISUAL target ${window.MnemorizedStoryContract.limits.visualTarget} words, absolute maximum ${window.MnemorizedStoryContract.limits.visualMax}. ANCHOR target ${window.MnemorizedStoryContract.limits.anchorTarget} words, preserving every necessary source qualifier. NARRATION is 2-3 concise spoken sentences.
- Draw one memorable cue for each coherent teaching unit; supporting lists and qualifiers remain in narration. A referral decision needs a clear decision hook, not a separate drawn item for every referral criterion.
- ANCHOR is the clinical fact only. NARRATION points to the exact visible object, explains the memory link, and teaches its source-supported fact.
- Use a single coherent room with large distinct objects. The opening target is ${window.MnemorizedStoryContract.limits.openingTargetMin}-${window.MnemorizedStoryContract.limits.openingTargetMax} words, absolute maximum ${window.MnemorizedStoryContract.limits.openingMax}, of architecture ONLY: walls, floor, ceiling, doorways. No people, props, clinical explanations, labels, or diagram layouts. This exact opening will be compiled into the image prompt.
- Make each VISUAL state the load-bearing relationship explicitly: who owns the object, what is already applied/connected/blocked, and what is distinct from neighboring props. Preparatory actions do not count as completed clinical actions. Use stable static states, not micro-poses or multi-hand choreography.
- Check the whole scene for overlapping locations, repeated silhouettes, and same-color fusion. Supporting props rest on a surface; critical contact is explicit. Simplify the physical interaction without changing its clinical association or deleting teaching units.
- Use strong shape or functional associations before sound-alike names. Preserve source qualifiers and uncertainty in every medical statement.
- No proprietary mnemonic scenes, characters, symbols, or layouts.

VISUAL ENCODING HIERARCHY: pure visual metaphor first, then metaphor with a short mnemonic name, then a name only when no stronger hook exists. Every hook must pass the silhouette test. Prefer a simple object interaction over an annotated list or a generic labeled prop. Use these sanctioned associations when relevant to the source facts:
${window.MnemorizedFirstAttempt?.metaphorLibrary(VISUAL_METAPHOR_LIBRARY) ?? VISUAL_METAPHOR_LIBRARY}

${clinicalContext}

Per-anchor tool fields: hook starts with the encoding strategy and explains the association; narration teaches the source-supported fact through the same cue; visual describes only drawable objects and relationships; anchor states the clinical fact; review is one line: "When you see [same image element] - remember [clinical fact]".
The bounded fields are not permission to omit a load-bearing relationship or source qualifier. Simplify the scene, not the medicine. Do not encode a count that contradicts the clinical classification or its learning text.`;

    const denseProtocol = isDenseProtocolTopic(topic, coreConcepts);
    const storyAttempts = [];
    const compactBody = (label, extraUser = '') => ({
      label,
      body: {
        model: CLAUDE_MODEL,
        max_tokens: 6144,
        system: compactStorySystem,
        ...window.MnemorizedStoryContract.request(requestedAnchorCount(topic) || 8),
        messages: [{
          role: 'user',
          content: extraUser ? `${storyUser}\n\n${extraUser}` : storyUser
        }]
      }
    });
    // Start with the bounded writer; the large advisor request repeatedly timed
    // out before reaching this same recovery path in real student runs.
    storyAttempts.push(compactBody(denseProtocol && !window.MnemorizedFirstAttempt?.isActive() ? 'dense-compact' : 'compact'));
    if (!window.MnemorizedFirstAttempt?.isActive()) storyAttempts.push(compactBody(
      denseProtocol ? 'dense-compact-strict' : 'compact-strict',
      `STRICT RETRY REQUIREMENT: Use every requested tool slot. Each VISUAL targets ${window.MnemorizedStoryContract.limits.visualTarget} words, maximum ${window.MnemorizedStoryContract.limits.visualMax}; no arrow glyphs, speech bubbles, exact-value clocks/dials/gauges, or more than one visible text surface. Use one object/character interaction and one location phrase. Preserve every teaching unit and source qualifier; group supporting details without deleting them. Exact values remain in NARRATION and ANCHOR.`
    ));
    if (!window.MnemorizedFirstAttempt?.isActive()) storyAttempts.push(compactBody(
      denseProtocol ? 'dense-visual-hard-gate' : 'visual-hard-gate',
      `FINAL VISUAL HARD GATE: Fill the complete requested anchor inventory. VISUAL target ${window.MnemorizedStoryContract.limits.visualTarget} words, maximum ${window.MnemorizedStoryContract.limits.visualMax}; no arrow glyphs, speech bubbles, exact-value clocks, dials, gauges, or precision plaques; at most one short mnemonic name on one object. No checklist ribbons, logbook rows or multi-label signs. Preserve all essential facts and qualifiers in learning text while using one strong shape-first relationship per VISUAL.`
    ));

    let storyValidation = null;
    let lastStoryError = null;

    for (let attemptIndex = 0; attemptIndex < storyAttempts.length; attemptIndex += 1) {
      if (operation !== forgeOperation || topic !== document.getElementById('topic').value.trim()) return;
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
        res = await claudeFetch(requestBody, `stage2-story-script-${attempt.label}`, {
          ...evidenceHeaders, ...(evidenceAvailable ? {'x-visual-preflight': 'true'} : {}),
        });
      } catch(fetchErr) {
        lastStoryError = new Error(fetchErr.message || 'Could not reach the provider proxy.');
        if (attemptIndex < storyAttempts.length - 1) continue;
        throw lastStoryError;
      }

      const rawText = await res.text().catch(() => '(could not read body)');
      if (operation !== forgeOperation || topic !== document.getElementById('topic').value.trim()) return;
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
        storyData = window.MnemorizedStoryContract.decode(raw, requestedAnchorCount(topic) || 8);
        txt = window.MnemorizedStoryContract.xml(storyData);
      } catch(parseErr) {
        lastStoryError = parseErr;
        if (raw?.stop_reason === 'max_tokens' && attemptIndex < storyAttempts.length - 1) continue;
        throw parseErr;
      }

      storyValidation = validateRequestedStory(storyData, requestedAnchorCount(topic));
      if (storyValidation.fatal.length) {
        showDebug(`STORY VALIDATION FAILED (${attempt.label})`, storyValidation);
        lastStoryError = new Error(`Scene Narrative validation failed: ${storyValidation.fatal.join(' ')}`);
        const retryableValidation = raw?.stop_reason === 'max_tokens'
          || storyValidation.fatal.some(message => /Too many anchors|visual|text surfaces|arrow glyphs|speech bubble/i.test(message));
        if (retryableValidation && attemptIndex < storyAttempts.length - 1) continue;
        if (retryableValidation && !window.MnemorizedFirstAttempt?.isActive()) {
          // Iterative micro-repair. One pass frequently can't drag a stubborn
          // over-length VISUAL under the word cap, and a single leftover fatal must
          // not abort an otherwise-complete scene. Re-run the repair, feeding the
          // still-failing XML back, up to a small budget; once the only remaining
          // fatals are word-count overflows, switch to the focused length repair.
          const MAX_MICRO_REPAIRS = 3;
          let repairInput = txt;
          for (let repairPass = 0; repairPass < MAX_MICRO_REPAIRS; repairPass++) {
            if (operation !== forgeOperation || topic !== document.getElementById('topic').value.trim()) return;
            const lengthOnly = storyValidation.fatal.every(m => /visual is \d+ words;/i.test(m));
            const repairedText = await repairStoryVisualFormat(repairInput, storyValidation, { lengthOnly, topic, operation, evidenceAvailable, originalStory:storyData });
            if (operation !== forgeOperation || topic !== document.getElementById('topic').value.trim()) return;
            if (!repairedText) break;
            storyData = parseStoryXml(repairedText);
            storyValidation = validateRequestedStory(storyData, requestedAnchorCount(topic));
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

    if (!currentRun()) return;
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
    if (!currentRun()) return;
    const box = document.getElementById('debug-box');
    const prev = box.textContent;
    box.style.display = 'block';
    box.textContent = `── STORY ERROR ──\n${e.message}\n\n── Previous debug output ──\n${prev}`;
    window.MnemorizedFirstAttempt?.fail();
    setStatus('story', '✗ ' + e.message.slice(0, 80), 'error');
    setStageDetail('story', 'Scene generation stopped before a usable script was created.');
    btn.disabled = false; btn.innerHTML = '✦ FORGE PALACE';
    return;
  }

  // ── STAGE 3: Image prompts ────────────────────────
  if (!currentRun()) return;
  setStatus('prompt', '✦ Building image prompts…', 'running');
  setStageDetail('prompt', 'Preparing constitution-guided illustration prompts from the generated anchor script.');

  try {
    const n = storyData.voLines.length;
    const pair = await prepareImagePromptPair(topic, storyData);
    if (!currentRun()) return;
    renderImagePromptPair(
      storyData,
      pair,
      '✓ Image prompts ready',
      `All ${n} anchors passed pre-render risk review. Pixel quality remains unverified until an independent image audit.`
    );

  } catch(e) {
    if (!currentRun()) return;
    setStatus('prompt', `✦ PROMPT ERROR ── ${e.message}`, 'error');
    showBody('prompt');
    setStageDetail('prompt', 'The palace script is still available, but image prompts failed to build.');
    console.error('Image prompt error:', e);
    window.MnemorizedFirstAttempt?.fail();
    invalidateImagePrompts();
    setCurrentPalaceData(storyData, '', '');
    if (currentQualityGateData) renderQualityGateResult(currentQualityGateData);
    btn.disabled = false;
    btn.innerHTML = '✦ FORGE PALACE';
    return;
  }

  // ── STAGE 4: Explicit image generation ──────────
  setStageDetail('prompt', 'Image prompts are ready. Use Generate Images when you want to spend an image request, or export the bundle for Gemini web QA.');

  btn.disabled = false;
  btn.innerHTML = '✦ FORGE PALACE';
  } finally {
    if (operation === forgeOperation) {
      btn.disabled = false;
      btn.innerHTML = '✦ FORGE PALACE';
    }
  }
}

// ── PWA service worker registration ──────────────────────────────

if ('serviceWorker' in navigator && window.location.protocol !== 'file:') {
  navigator.serviceWorker
    .register('/sw.js', { updateViaCache: 'none' })
    .then(registration => registration.update())
    .catch(() => {});
}
