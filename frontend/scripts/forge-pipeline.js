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

const ANTI_META_TEXT = 'TEXT RULES: Do NOT render any floating labels, zone names, category descriptions, ' +
  'or meta-commentary as visible text in the image. The ONLY text that should appear is text that is ' +
  'physically part of an object in the scene — written on signs, sticky notes, labels, screens, bottles, ' +
  'chalkboards, or other in-world surfaces. No floating captions. No zone labels. No anchor descriptions.';

const PRECISION_TEXT_RULE = 'PRECISION TEXT EXCEPTION: short numbers, thresholds, units, and compact formulas are allowed when they are the tested fact. ' +
  'They must be physically attached to the mnemonic object as a plaque, dial, ruler mark, scale beam, gauge face, or chalk mark. ' +
  'Do not use text as the whole mnemonic: every precision label must sit on a strong non-text visual device that still reads by silhouette. ' +
  'Keep precision text large, sparse, accurate, and readable; no sentences or paragraph labels.';

const ANCHOR_LEGIBILITY_RULE = 'ANCHOR LEGIBILITY RULE: every anchor must be large enough to identify at normal 1024px image size. ' +
  'No anchor may become tiny shelf clutter. Give each anchor clear empty space, a distinct silhouette, and enough scale to read its key shape before reading any label. ' +
  'If a shelf or wall contains multiple anchors, stagger them vertically and enlarge each one instead of lining up small similar props.';

const EXACT_LABEL_RULE = 'EXACT LABEL RULE: if a visual specifies a short label, copy it exactly. ' +
  'Do not invent alternate spellings, abbreviations, or nonsense words. Sound-alike character names must appear exactly when the name carries the mnemonic. ' +
  'If exact text would be too small or uncertain, replace it with a larger physical symbol instead of misspelling it.';

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

function buildAnchorLines(anchors) {
  return anchors.map(v => `  (${v.zone.toLowerCase()}) Anchor ${v.n}: ${v.visual}`).join('\n');
}

function trimWords(text, maxWords) {
  const words = String(text || '').trim().split(/\s+/).filter(Boolean);
  if (words.length <= maxWords) return words.join(' ');
  return words.slice(0, maxWords).join(' ') + '...';
}

function buildImageAnchorLines(anchors, concise = false) {
  return anchors.map(v => {
    const visual = trimWords(condenseForImage(v.visual), concise ? 18 : 32);
    const anchor = v.anchor ? ` Encodes: ${trimWords(v.anchor, concise ? 18 : 32)}` : '';
    if (concise) {
      return `  (${v.zone.toLowerCase()}) Anchor ${v.n}: ${visual}.${anchor}`;
    }
    const hook = v.hook ? ` Hook: ${trimWords(v.hook, 24)}.` : '';
    return `  (${v.zone.toLowerCase()}) Anchor ${v.n}:${hook} Visual: ${visual}.${anchor}`;
  }).join('\n');
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
    `The words "Hook" and "Encodes" are invisible design guidance only — do NOT render them as text. ` +
    `Preserve clear spatial hierarchy: left/center/right/foreground/background zones must stay readable and uncluttered. ` +
    `Each anchor should be recognizable by its SHAPE and SILHOUETTE first. ` +
    `${ANCHOR_LEGIBILITY_RULE} ` +
    `Text labels are secondary and optional — if present, maximum 3 words per ordinary label. ` +
    `${PRECISION_TEXT_RULE} ` +
    `${EXACT_LABEL_RULE} ` +
    `SCENE TEXT BUDGET: maximum 12 ordinary text labels plus up to 4 precision labels for numbers/formulas in the ENTIRE image. Character names and short numbers count. ` +
    `Zone hints in parentheses guide placement — do NOT render zone text:\n\n` +
    buildImageAnchorLines(assigned, concise) + '\n\n' +
    `All ${n} anchors must be present and visually distinct. ` +
    `Do NOT add labels to room surfaces, walls, beams, or background objects. ` +
    `Maintain same lighting, color palette, and atmosphere.`;
}

function clampImagePrompt(prompt, maxChars = IMAGE_PROMPT_MAX_CHARS) {
  const text = String(prompt || '').trim();
  if (text.length <= maxChars) return text;
  return text.slice(0, maxChars - 180).replace(/\s+\S*$/, '') +
    '\n\nFINAL HARD LIMIT: preserve all numbered anchors above; do not add extra labels or checklist text.';
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
    prompt2: data.prompt2,
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
  return !/^e\.g\./.test(normalized) && normalized.length > 24;
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

async function generateImages() {
  const p1 = document.getElementById('prompt-copy-1')?.value;
  const p2 = document.getElementById('prompt-copy-2')?.value;
  if (!p1 && !p2) { alert('Forge a palace first to generate image prompts.'); return; }
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
    setStatus('prompt', `Prompt rebuild failed: ${error.message}`, 'error');
    setStageDetail('prompt', 'The repaired script was kept, but image prompts need to be regenerated.');
  }
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

    const demoP1 = SKETCHY_STYLE_ROOM + '\n\n' + D.prompt1_sample + ', aspect ratio 16:9, flat 2D cartoon';

    const demoP2 = SKETCHY_STYLE + '\n\n' + D.prompt1_sample +
      ', aspect ratio 16:9, flat 2D cartoon.\n\n' +
      `${ANTI_META_TEXT}\n\n` +
      `SCENE OBJECT RULE: Do NOT label or name any part of the room itself. ` +
      `Background surfaces are unlabeled.\n\n` +
      `Add ALL ${n} of the following medical mnemonic anchors to the scene. ` +
      `Anchors may be objects, characters/figures, or interactive elements — they are VISUAL MNEMONICS, not labeled props. ` +
      `The words "Hook" and "Encodes" are invisible design guidance only — do NOT render them as text. ` +
      `Preserve clear spatial hierarchy: left/center/right/foreground/background zones must stay readable and uncluttered. ` +
      `Each anchor should be recognizable by its SHAPE and SILHOUETTE first. ` +
      `${ANCHOR_LEGIBILITY_RULE} ` +
      `Text labels are secondary and optional — if present, maximum 3 words per ordinary label. ` +
      `${PRECISION_TEXT_RULE} ` +
      `${EXACT_LABEL_RULE} ` +
      `SCENE TEXT BUDGET: maximum 12 ordinary text labels plus up to 4 precision labels for numbers/formulas in the ENTIRE image. Character names and short numbers count. ` +
      `Zone hints in parentheses guide placement — do NOT render zone text:\n\n` +
      buildImageAnchorLines(assigned) + '\n\n' +
      `All ${n} anchors must be present and visually distinct. ` +
      `Do NOT add labels to room surfaces, walls, beams, or background objects. ` +
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
  const evidenceAvailable = !!(authState.user && appConfig.medicalKnowledgeEnabled && backendState.medicalKnowledgeConfigured);
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

Output ONLY these two XML tags, nothing else:

<core_concepts>The 8-12 most important, data-backed clinical facts that MUST be encoded — aim for comprehensive board-level coverage with ZERO important omissions. One per line. Include: diagnostic criteria, key thresholds/numbers, mechanism, first-line management steps, critical safety checks, common pitfalls, and resolution/disposition criteria. EVERY specific number, threshold, dose, duration, angle, and scoring range must be EXACT per current guidelines — no approximations, no rounding, no merging different values into one. If the topic has a well-known systematic approach (e.g. EKG interpretation steps, trauma primary survey), cover EVERY step — do not skip any.</core_concepts>
<scene_logic>How to spatially arrange these concepts in a single illustrated scene — how the eye moves left-to-right and foreground-to-background. 8-10 anchors need distinct zones across left, center, right, foreground, and background areas.</scene_logic>`,
        messages: [{ role: 'user', content: `Clinical topic: ${topic}\nLearner: ED/ICU physician — needs precise, high-yield anchors.` }]
      }), 'stage1-clinical-context', evidenceHeaders);
    setStatus('story', '✦ Analyzing topic…', 'running');
    setStageDetail('story', 'Extracting high-yield clinical concepts and a spatial scene plan.');
    const ctxRaw = await ctxRes.json();
    const ctxTxt = parseProviderContent(ctxRaw, 'Clinical Context');
    const core   = extractXmlTag(ctxTxt, 'core_concepts');
    const logic  = extractXmlTag(ctxTxt, 'scene_logic');
    if (core || logic) {
      clinicalContext = `CLINICAL DESIGN CONTEXT — bake these facts and spatial logic into the scene:\n\nCORE CONCEPTS:\n${core}\n\nSCENE LAYOUT:\n${logic}\n\nEvery anchor must encode a specific fact from above.`;
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
- Do NOT reuse named scenes, recurring characters, or proprietary symbols from existing commercial visual mnemonic products. Learn from the design principles; invent fresh cues.
- Made of materials that render flat: wood, paper, brick, chalkboard, fabric, cork, cardboard, stone, ceramic
- BEST settings: bars, pubs, workshops, kitchens, old shops, speakeasies, market stalls, barber shops, diners, courtrooms, train stations
- AVOID: glass, chrome, metal, screens, modern clinical equipment, sci-fi technology, holographic displays — these fight the flat hand-drawn style
- The setting is a spatial memory map, not a backdrop. Each anchor must belong to the same environment and occupy a memorable zone.

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

VISUAL MNEMONIC DESIGN — THIS IS THE HEART OF THE PRODUCT:
These principles are inspired by visual mnemonic education, but every scene and symbol must be original. The goal: a student recalls the medical fact from the SHAPE, IDENTITY, RELATIONSHIP, and POSITION of the cue even with ALL text removed.

ENCODING HIERARCHY — try each level in order, use the FIRST that fits:
1. SOUND-ALIKE (strongest): Object or character NAME sounds like the medical term. Invent a fresh phonetic pun for the term; do not reuse known commercial mnemonic symbols. Phonetic puns are powerful when they are clean and obvious.
2. LOOK-ALIKE: Object SHAPE mirrors a number, symbol, organ, or process. Fork with 3 prongs → triad. Cracked wall → inhibition. Y-shaped branch → antibody. A figure-8 knot → chromosome 8.
3. FUNCTIONAL ANALOGY: Object BEHAVIOR mirrors the clinical mechanism. Bellows pushing air → bronchodilator. Cork blocking pipe → antagonist. Overflowing bucket → excess/toxicity. Key in lock → agonist. Guard blocking door → immune defense.
4. CONTRAST/THRESHOLD: Two OPPOSING objects encode a decision point. Big vs small, open vs locked, hot vs cold, thumbs-up shelf vs thumbs-down shelf, short rope vs long rope.
5. SPATIAL: POSITION encodes meaning. Escalation goes up (stairs, shelves). Sequence goes left-to-right. Danger is isolated behind barriers. Exit/door = discharge criteria. Basement = last-resort therapy.
6. LABELED TEXT (weakest — LAST RESORT): A sign or tag with 1-3 words. If you resort to this, the anchor is weak. Go back and try levels 1-5 harder.

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

FORMULA RULE / PRECISION TEXT RULE: Short numbers, thresholds, units, and compact formulas are allowed when they are the tested fact. They must be physically attached to a mnemonic device: plaque, dial, ruler mark, scale beam, gauge face, tag, or chalk mark. Do not make text the entire mnemonic. A formula anchor still needs a silhouette-first visual analogy: scale for anion gap, paired rulers for delta-delta, thermometer/ruler/gauge for Winter's formula, locked gauge cabinet for osmol gap.

LARGE NUMBER RULE: Do NOT encode numbers greater than 12 by asking for exact repeated object counts. Image generators cannot reliably draw exactly 30 soldiers, 40 tablets, or 90 items. Use one strong object with an exact plaque, gauge, dial, ruler, or stamped marker instead.

HOOK/VISUAL CONSISTENCY RULE: Do not claim an anchor is label-free if the tested fact requires a number or formula label. If precision text is necessary, make it intentional and attached to a visual device.

SCENE TEXT BUDGET: The ENTIRE scene should have at most 12 ordinary short text labels plus up to 4 precision labels for numbers/formulas. Ordinary labels are 1-3 words max. Precision labels may be formulas or thresholds, but must be sparse, readable, and attached to a strong visual device. Prioritize: medically essential numbers/formulas > character names (sound-alikes) > optional flavor labels.

EXACT LABEL RULE: If a visual specifies a short label, copy it exactly. Do not invent alternate spellings, abbreviations, or nonsense words. Sound-alike character names must appear exactly when the name carries the mnemonic. If exact text would be too small or uncertain, replace it with a larger physical symbol instead of misspelling it.

WHAT TO AVOID:
- Plain checklists, generic posters, ordinary clipboards, labeled bottles — these fail the silhouette test
- Any anchor whose ONLY mnemonic value is text printed on it
- Medical equipment used literally (stethoscope for "auscultation" is lazy — use a giant ear trumpet or a character with comically oversized ears)
- Long text strings on any surface — the image generator cannot reliably render more than 3-4 words per label
- Multiple jars, bottles, or containers that would look identical as silhouettes — each anchor needs a unique shape

VISUAL DESCRIPTION RULES:
- MAXIMUM 30 WORDS per visual description
- Aim for no more than two visible text elements per anchor. A visible text element is any label, number/formula plaque, tag, banner, stamp, dial, gauge, sign, or written word.
- Do not cram a list of labels into one visual. If an anchor needs several facts, encode most with shape/scale/position/action and reserve text only for the essential number or short mnemonic name.
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

CRITICAL: When grouping sub-items, do NOT lose specificity. If two sub-items have DIFFERENT numbers (different scoring ranges, different time limits, different angles, different doses), the visual description and narration must clearly show BOTH distinct values. For instance, if arms are tested for 10 seconds and legs for 5 seconds, the visual must show "10 SEC" AND "5 SEC" as separate labels — never collapse them into one number.
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
- Prefer silhouette-first objects/characters over text labels. Text is allowed only for exact numbers/formulas and must be attached to a device.
- Avoid checklists, generic posters, ordinary clipboards, repeated same-shaped props, modern screens, glass, chrome, and medical equipment used literally.
- VISUAL is max 24 words. ANCHOR is max 30 words. NARRATION is 2-3 concise spoken sentences.
- No proprietary mnemonic scenes, characters, symbols, or layouts.

${clinicalContext}

Schema:
<vo_line>
HOOK: [strategy] - why the visual encodes the fact
NARRATION: [concise spoken explanation]
VISUAL: [drawn object/character, position, essential precision label only if needed]
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
      'STRICT RETRY REQUIREMENT: The final output is invalid if it contains more than 10 <vo_line> blocks, any VISUAL over 30 words, arrow glyphs, speech bubbles, or more than two visible text surfaces in one anchor. Merge related sub-items until there are exactly 8-10 anchors. Do not omit facts; encode dense clinical facts with silhouette-first object interactions, scale, position, containment, blocking, and contrast. Use text only for essential numbers/formulas.'
    ));
    storyAttempts.push(compactBody(
      denseProtocol ? 'dense-visual-hard-gate' : 'timeout-visual-hard-gate-fallback',
      'FINAL VISUAL HARD GATE: Rewrite the scene with 8-10 anchors and make every VISUAL pass these rules: 24 words or fewer; no arrow glyphs; no speech bubbles; no more than one quoted label per anchor; no more than two text-bearing objects per anchor; no checklist ribbons, no logbook rows, no multi-label signs. Preserve all essential medical facts by moving details into NARRATION and ANCHOR, while the VISUAL uses one strong object interaction plus at most one precision plaque.'
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
    await runMedicalQualityGate(storyData, coreConcepts);
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
