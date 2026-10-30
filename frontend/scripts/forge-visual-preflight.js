// Pre-render risk review, not an image grade or a clinical certification.
(function (root) {
  'use strict';
  const VERSION = 'visual-preflight-v2';
  const MAX_REPAIRS = 2;
  let report = null;
  let binding = null;
  let epoch = 0;

  const clone = value => JSON.parse(JSON.stringify(value));
  function parseReview(text) {
    const trimmed = String(text).trim();
    const fenced = trimmed.match(/^```(?:json)?\s*\n([\s\S]*?)\n```$/i);
    return JSON.parse(fenced ? fenced[1] : trimmed);
  }
  const key = (topic, story) => JSON.stringify({ topic, story });
  async function hash(text) {
    const bytes = await root.crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(bytes), n => n.toString(16).padStart(2, '0')).join('');
  }
  function reset() { epoch++; report = null; binding = null; }
  function invalidate() {
    epoch++; binding = null;
    if (report?.status === 'ready' || report?.status === 'reviewing') report.status = 'stale';
  }

  function requireEvidence(story, gate) {
    if (!Array.isArray(story?.required_concepts) || !story.required_concepts.length) {
      throw new Error('Preflight requires an independent clinical coverage contract.');
    }
    if (gate?.verdict !== 'ready_for_review' || gate.evidence_status !== 'matched' ||
        !Array.isArray(gate.evidence) || !gate.evidence.length ||
        !Array.isArray(gate.missing_from_generation) || gate.missing_from_generation.length ||
        !Array.isArray(gate.ungrounded_concepts) || gate.ungrounded_concepts.length) {
      throw new Error('Medical evidence has not cleared. Repair the source/coverage problem before image preflight.');
    }
  }

  function inspect(story) {
    const errors = [], risks = [], seen = new Set(), ids = new Set();
    const {limits, wordCount} = root.MnemorizedStoryContract;
    if (typeof story?.opening !== 'string' || !story.opening.trim() || wordCount(story.opening) > limits.openingMax) {
      errors.push(`Scene opening must be a nonempty architecture description of at most ${limits.openingMax} words.`);
    }
    if (!Array.isArray(story?.voLines) || !story.voLines.length) errors.push('No anchors.');
    (story?.voLines || []).forEach((line, index) => {
      if (!Number.isInteger(line.n) || line.n !== index + 1 || ids.has(line.n)) errors.push('Anchor IDs must be unique and sequential.');
      ids.add(line.n);
      for (const field of ['visual', 'hook', 'anchor', 'narration']) {
        if (typeof line[field] !== 'string' || !line[field].trim()) errors.push(`Anchor ${line.n}: missing ${field}.`);
      }
      const visual = String(line.visual || '').trim().replace(/\s+/g, ' ');
      if (seen.has(visual.toLowerCase())) errors.push(`Anchor ${line.n}: duplicate visual.`);
      seen.add(visual.toLowerCase());
      try {
        if (typeof imageAnchorVisual === 'function') imageAnchorVisual(line, index);
        if (typeof extractRenderableLabels === 'function') extractRenderableLabels([line]);
      } catch (error) {
        risks.push({n: line.n, message: error.message.replace(/^Image anchor \d+\b/, `Image anchor ${line.n}`), blocking: true});
      }
      // These are risk signals for the critic, never a predicted pixel score.
      const signals = [
        [/\b(?:about to|preparing to|ready to|reaches for|approaches)\b/i, 'Action may be preparatory rather than completed.'],
        [/\b(?:tiny|faint|miniature|subtle|small print)\b/i, 'Critical detail may be too small.'],
        [/\b(?:passes|hands over|simultaneously|while holding)\b/i, 'Competing actions or a handoff may obscure ownership.'],
        [/\b(?:represents|symbolizes|encodes|signifies)\b/i, 'Meaning is asserted instead of visibly specified.'],
      ];
      signals.forEach(([pattern, message]) => { if (pattern.test(visual)) risks.push({n: line.n, message}); });
    });
    return { errors, risks };
  }

  function validateReview(value, story, evidence) {
    value = clone(value);
    const fail = message => { throw new Error('Incomplete visual preflight review: ' + message); };
    if (!value || !['supported', 'needs_repair', 'source_gap'].includes(value.clinical_status) ||
        !Array.isArray(value.clinical_findings)) fail('clinical disposition missing.');
    if (value.clinical_status !== 'supported' && !value.clinical_findings.length) fail('clinical failure has no explanation.');
    if (value.clinical_status === 'supported' && value.clinical_findings.length) fail('contradictory clinical clearance.');
    if (value.clinical_status !== 'supported') {
      value.clinical_findings.forEach(finding => {
        if (!finding || typeof finding.issue !== 'string' || !finding.issue.trim()) fail('clinical finding needs a concrete issue.');
        if (value.clinical_status === 'needs_repair') {
          const owner = finding.n === null ? story : story.voLines.find(line => line.n === finding.n);
          const fieldValid = finding.n === null ? finding.field === 'review_script'
            : story.voLines.some(line => line.n === finding.n) && ['anchor', 'narration'].includes(finding.field);
          if (!fieldValid || !Array.isArray(finding.source_refs) || !finding.source_refs.length ||
              finding.source_refs.some(ref => !evidence.some(e => e.source_key === ref.source_key && e.page_start === ref.page_start))) {
            fail('clinical repair lacks a valid field and retrieved source reference.');
          }
          if (typeof finding.quote !== 'string' || !finding.quote.trim() ||
              (finding.quote.trim().split(/\s+/).length < 4 && finding.quote !== owner[finding.field]) ||
              !owner[finding.field].includes(finding.quote)) fail('clinical finding lacks an exact quote from the current target field.');
        }
      });
      // Source/clinical failure returns early: do not spend the response budget
      // reviewing drawing details for a lesson whose meaning is not yet approved.
      return value;
    }
    if (!Array.isArray(value.anchors) || value.anchors.length !== story.voLines.length) fail('not every anchor was reviewed.');
    const rowsById = new Map(value.anchors.map(row => [row?.n, row]));
    if (rowsById.size !== story.voLines.length || story.voLines.some(line => !rowsById.has(line.n))) {
      fail('anchor IDs must cover the lesson exactly once.');
    }
    value.anchors = story.voLines.map(line => rowsById.get(line.n));
    value.anchors.forEach((row, index) => {
      const line = story.voLines[index];
      if (row.n !== line.n || !['ready', 'repair'].includes(row.status) ||
          typeof row.why !== 'string' || !row.why.trim() || !Array.isArray(row.risks)) fail(`anchor ${line.n} is malformed.`);
      if (row.repair_scope != null && !['visual', 'redesign'].includes(row.repair_scope)) fail(`anchor ${line.n} has an invalid repair scope.`);
      row.risks = row.risks.map(risk => {
        const text = typeof risk === 'string' ? risk : risk?.risk;
        if (typeof text !== 'string' || !text.trim()) fail(`anchor ${line.n} has a malformed risk.`);
        return text;
      });
      if (row.status === 'ready' && row.risks.length) {
        row.reported_status = 'ready'; row.status = 'repair';
      }
      if (row.status === 'repair' && !['visual', 'redesign'].includes(row.repair_scope)) fail(`anchor ${line.n} needs a valid repair scope.`);
      if (typeof row.relationship_quote !== 'string' || row.relationship_quote.trim().split(/\s+/).length < 3 ||
          !line.visual.includes(row.relationship_quote)) fail(`anchor ${line.n} cites a relationship absent from its VISUAL.`);
      if (row.status === 'repair' && !row.risks.length) fail(`anchor ${line.n} needs a concrete repair reason.`);
      if (value.clinical_status === 'supported') {
        if (!Array.isArray(row.source_refs) || !row.source_refs.length) fail(`anchor ${line.n} lacks source attribution.`);
        for (const ref of row.source_refs) {
          if (!ref.source_key || !evidence.some(e => e.source_key === ref.source_key && e.page_start === ref.page_start)) {
            fail(`anchor ${line.n} cites a source outside the retrieved evidence.`);
          }
        }
      }
    });
    if (!value.scene || !['ready', 'repair'].includes(value.scene.status) || !Array.isArray(value.scene.issues)) fail('scene review missing.');
    if (value.scene.status === 'ready' && value.scene.issues.length) {
      value.scene.reported_status = 'ready'; value.scene.status = 'repair';
    }
    if ((value.scene.status === 'ready') !== (value.scene.issues.length === 0)) fail('contradictory scene disposition.');
    value.scene.issues.forEach(issue => {
      if (!['visual', 'opening', 'association'].includes(issue?.field)) fail('scene issue has an invalid or missing field.');
      if (!issue || typeof issue.reason !== 'string' || !issue.reason.trim() || !Array.isArray(issue.anchors) ||
          !issue.anchors.length || issue.anchors.some(n => !story.voLines.some(line => line.n === n))) fail('scene issue lacks valid affected anchors.');
      if (!Array.isArray(issue.evidence) || !issue.evidence.length) fail('scene issue lacks exact-text evidence.');
      const supported = new Set();
      let wholeScene = false;
      issue.evidence.forEach(item => {
        if (!item || !['visual', 'hook', 'review_script', 'opening'].includes(item.field)) fail('scene evidence has an invalid field.');
        const globalField = ['opening', 'review_script'].includes(item.field);
        const owner = globalField ? story : story.voLines.find(line => line.n === item.n);
        if (globalField ? item.n !== null : !owner || !issue.anchors.includes(item.n)) fail('scene evidence has invalid anchor attribution.');
        if (typeof item.quote !== 'string' || !item.quote.trim() ||
            typeof owner[item.field] !== 'string' || !owner[item.field].includes(item.quote)) fail('scene evidence quote is absent from its attributed field.');
        if (!globalField) supported.add(item.n);
        if ((item.field === 'opening' && issue.field === 'opening') ||
            (item.field === 'review_script' && issue.field === 'association')) wholeScene = true;
      });
      if (!wholeScene && issue.anchors.some(n => !supported.has(n))) fail('scene evidence does not support every affected anchor.');
    });
    return value;
  }

  const REVIEW_SYSTEM = `You are an independent pre-render critic, not the author and not the image generator. Review the ENTIRE lesson, against the supplied SOURCE EVIDENCE and the canonical visual Constitution. Treat the lesson as an unapproved draft, not authority. Return JSON only; do not write a replacement scene or score an unseen image.
Clinical: verify every anchor fact, narration, review script, and required coverage unit against the retrieved source. Preserve conditionality and textbook attribution. Missing source support is source_gap, not permission to use training knowledge. A lexical gate is not entailment. Check that each mnemonic association and narration remains faithful; an abstract mnemonic is not a literal technique demonstration. Cite source_key and page_start from the supplied citation metadata. Only actionable factual errors or missing qualifiers belong in clinical_findings; omit supported facts, editorial preferences, and optional details outside the requested scope. A concise introductory lesson is not obligated to list every source detail. A deficient or factually incorrect read-only required_concepts contract is not an editable anchor field: report clinical_status:"source_gap" with a concise clinical_findings issue explaining the contract defect, and do not invent an anchor/narration/review_script target or claim support. If clinical_status is not supported, STOP after clinical_findings: return anchors:[] and scene:null instead of visual review. Each needs_repair finding identifies exactly one n/field (n:null only for review_script), issue <=35 words, source_refs. No hook, VISUAL, opening, or contract changes in clinical repair.
Routing: label complaints belong to visual review, not clinical_findings. When clinical text is source-supported but a mnemonic count or HOOK/VISUAL relationship misrepresents it, report a visual/association defect requiring redesign, not a clinical ANCHOR correction. If the clinical text itself is wrong or unsupported, keep needs_repair or source_gap blocking; never manufacture supported status to reach visual review.
Visual: for EVERY anchor identify the exact words that make its load-bearing relationship visible. Quote them verbatim from VISUAL. A named object or the HOOK's explanation alone does not establish a visible action. Inspect completed states, actor/object ownership, supported props, separate silhouettes, contact of modifiers with their target, and preservation of multi-person states. A clue may retrieve a coherent decision with supporting values in narration; do not demand one drawn prop per fact. Do not reject valid symbolic hooks for not being literal medical procedures. Reject medically misleading implications.
Scene: the exact opening is compiled with every VISUAL. It must describe only one continuous room's architecture, without new props, characters, medical explanations, or competing instructions. Check all anchors together for duplicate/confusable silhouettes, same-color fusion, conflicting locations, overcrowded small cues, competing actions/held items, and contradictory states. Only require repair for a concrete conflict or missing load-bearing relationship; density/complexity alone is not a calibrated rejection threshold. Do not add micro-poses, label inventories, grids, or tiny apparatus parts. A functioning static object-state or simple relation is sufficient; every anchor need not have a human actor. Clinical or narration changes must be flagged, never disguised as a visual-only repair.
Compiler boundary and review discipline: ONLY opening and VISUAL strings reach the deterministic image compiler. HOOK, narration and review_script are learning text, not image instructions. A mismatch between learning text and VISUAL is a recall-consistency defect, not text leakage from an uncompiled field. Count every explicitly described object before alleging a count mismatch, including separate objects beside a group. Mnemonic names are original associations; the clinical fact requires a textbook citation, not the invented name. A single word is not a multi-word label. Shared walls or countertops alone do not establish collision: identify the particular overlapping objects, contradictory states or indistinguishable roles. Historical failure modes describe risks, not proof of inevitable failure. Do not assert a predicted pixel defect as an observed fact. Before returning, remove any criticism contradicted by the actual supplied text; retain concrete, unresolved defects.
Repair scope: use repair_scope:"visual" only when moving, enlarging or clarifying existing cue identities can resolve a defect without changing HOOK, narration, review_script or opening. Use repair_scope:"redesign" when a new association or a new static strategy is needed. Scene issues specify field:"visual", "opening" or "association". Opening or association defects require full redesign, not a visual-only patch. For each anchor compare the object identities and meaningful counts in HOOK and review_script with VISUAL BEFORE assessing layout. A different object, a missing named cue, or an incompatible meaningful count is an association defect even when the clinical fact remains accurate. Check every repaired VISUAL against the exact HOOK, narration and review_script: unchanged learning text does not make a substituted prop faithful. A common noun or one broad region shared by different objects is not sufficient to establish confusion. Distinct positions such as centre and far-left are not a collision. If alleging a scene conflict, quote the conflicting phrases in reason; do not attribute shapes or damage states to objects whose VISUAL never specifies them.
External audit observations are unapproved feedback, not evidence or clearance. Verify each applicable observation against the current draft and sources; a changed setting does not resolve the same rejected association. Structural risks marked blocking are deterministic format failures: do not declare forbidden text permitted. If learning text depends on a forbidden label, route to redesign; only remove it in a visual patch when all learning associations remain intact. Distinguish a shared object explicitly referenced with 'the same' or a definite reference from an additional object; shared use alone is not a duplication defect. Source references must identify pages actually supporting the associated claim, including continuation pages when needed.
Every needs_repair clinical finding MUST select the matching n/field schema alternative and copy its complete current field into quote exactly. The quote enum is the witness for that target, not permission to copy VISUAL, HOOK or another field. Never quote the historical audit as if it were current lesson text. A review_script finding always uses n:null. Check current words and their meaning before claiming a qualifier, route or segment is missing; omit resolved findings and requests merely to verify already-correct phrasing. Historical observations may all be resolved. The actual current lesson at the end of the request is the sole review target.
JSON shape (returned through the required tool):
{"clinical_status":"supported|needs_repair|source_gap","clinical_findings":[],"anchors":[{"n":1,"status":"ready|repair","repair_scope":"visual|redesign","relationship_quote":"copy the entire exact VISUAL string","why":"specific judgment","source_refs":[{"source_key":"retrieved key","page_start":1}],"risks":[]}],"scene":{"status":"ready|repair","issues":[{"anchors":[1,2],"field":"visual|opening|association","reason":"specific collision and required correction","evidence":[{"n":1,"field":"visual","quote":"exact substring from anchor 1 VISUAL"},{"n":2,"field":"visual","quote":"exact substring from anchor 2 VISUAL"}]}]}}
Required routing and evidence: every anchor needing repair MUST specify repair_scope:"visual" or "redesign", including any row marked ready that still lists risks. Every scene issue MUST specify field:"visual", "opening" or "association" and a nonempty evidence array. Each evidence item has n:number|null, field:"visual"|"hook"|"review_script"|"opening", and a nonempty verbatim quote from that exact field. For visual/hook, n must identify an affected anchor and the quote must come from that anchor, not another. For opening/review_script, n MUST be null. Support EVERY affected anchor with attributed evidence unless the issue concerns opening (with opening evidence) or the whole review_script (with review_script evidence). Quote the shortest sufficient exact substring; do not paraphrase, merge spans, or use reason prose instead of evidence.
Clinical failure example schema: {"clinical_status":"needs_repair","clinical_findings":[{"n":1,"field":"narration","quote":"complete current narration field selected from its enum","issue":"specific factual correction","source_refs":[{"source_key":"retrieved key","page_start":1}]}],"anchors":[],"scene":null}.
Read-only contract failure example: {"clinical_status":"source_gap","clinical_findings":[{"issue":"The required_concepts contract asserts X, but the retrieved evidence supports Y."}],"anchors":[],"scene":null}.
COMPACT RESPONSE CONTRACT: JSON only, no essay or Markdown. Each why <=18 words; each risk <=18 words, at most two per anchor. Risks are STRINGS only, never objects: ["concrete defect"]. Each scene reason <=25 words. Copy each entire VISUAL verbatim into relationship_quote, preserving punctuation and pronouns; do not paraphrase or join separated spans. At most four scene issues; combine related conflicts. Target <=2400 output tokens. Preserve every anchor row when clinically supported. Ready rows have no unresolved risks. A supported clinical review has no clinical_findings. Scene ready has no issues. Do not claim evidence you cannot inspect.`;

  async function review(topic, story, gate, signals, round, expertReview, externalFeedback) {
    const anchorIds = story.voLines.map(line => line.n);
    const sourceRefs = [...new Map(gate.evidence.map(({source_key, page_start}) =>
      [JSON.stringify([source_key, page_start]), {source_key, page_start}])).values()];
    const referenceSchema = {anyOf: sourceRefs.map(({source_key, page_start}) => ({type: 'object', properties: {
      source_key: {type: 'string', enum: [source_key]},
      page_start: {type: 'integer', enum: [page_start]},
    }, required: ['source_key', 'page_start'], additionalProperties: false}))};
    const clinicalTargets = story.voLines.flatMap(line => ['anchor', 'narration'].map(field =>
      ({n: line.n, field, text: line[field]})));
    if (typeof story.review_script === 'string' && story.review_script.trim()) {
      clinicalTargets.push({n: null, field: 'review_script', text: story.review_script});
    }
    const findingSchema = {anyOf: [
      {type: 'object', properties: {issue: {type: 'string'}}, required: ['issue'], additionalProperties: false},
      ...clinicalTargets.map(({n, field, text}) => ({type: 'object', properties: {
        n: n === null ? {type: 'null'} : {type: 'integer', enum: [n]},
        field: {type: 'string', enum: [field]}, quote: {type: 'string', enum: [text]}, issue: {type: 'string'},
        source_refs: {type: 'array', items: referenceSchema, minItems: 1},
      }, required: ['n', 'field', 'quote', 'issue', 'source_refs'], additionalProperties: false})),
    ]};
    const evidenceSchema = {type: 'object', properties: {
      n: {anyOf: [{type: 'integer', enum: anchorIds}, {type: 'null'}]},
      field: {type: 'string', enum: ['visual', 'hook', 'review_script', 'opening']}, quote: {type: 'string'},
    }, required: ['n', 'field', 'quote'], additionalProperties: false};
    const schema = {type: 'object', properties: {
      clinical_status: {type: 'string', enum: ['supported', 'needs_repair', 'source_gap']},
      clinical_findings: {type: 'array', items: findingSchema},
      anchors: {type: 'array', items: {type: 'object', properties: {
        n: {type: 'integer', enum: anchorIds}, status: {type: 'string', enum: ['ready', 'repair']},
        repair_scope: {anyOf: [{type: 'string', enum: ['visual', 'redesign']}, {type: 'null'}]},
        relationship_quote: {type: 'string'}, why: {type: 'string'},
        source_refs: {type: 'array', items: referenceSchema, minItems: 1}, risks: {type: 'array', items: {type: 'string'}},
      }, required: ['n', 'status', 'repair_scope', 'relationship_quote', 'why', 'source_refs', 'risks'], additionalProperties: false}},
      scene: {anyOf: [{type: 'null'}, {type: 'object', properties: {
        status: {type: 'string', enum: ['ready', 'repair']}, issues: {type: 'array', items: {type: 'object', properties: {
          anchors: {type: 'array', items: {type: 'integer', enum: anchorIds}, minItems: 1},
          field: {type: 'string', enum: ['visual', 'opening', 'association']}, reason: {type: 'string'},
          evidence: {type: 'array', minItems: 1, items: evidenceSchema},
        }, required: ['anchors', 'field', 'reason', 'evidence'], additionalProperties: false}},
      }, required: ['status', 'issues'], additionalProperties: false}]},
    }, required: ['clinical_status', 'clinical_findings', 'anchors', 'scene'], additionalProperties: false};
    const response = await claudeFetch({
      model: expertReview ? CLAUDE_ADVISOR_MODEL : CLAUDE_MODEL,
      max_tokens: 5000,
      system: REVIEW_SYSTEM,
      tools: [{name: 'submit_visual_preflight_review', description: 'Submit the complete source-grounded visual preflight review.', strict: true, input_schema: schema}],
      tool_choice: {type: 'tool', name: 'submit_visual_preflight_review', disable_parallel_tool_use: true},
      messages: [{role: 'user', content: JSON.stringify({
        external_audit_observations: externalFeedback || '',
        learner_request: topic, citations: gate.evidence, structural_risks: signals.risks, lesson: story,
      })}],
    }, `visual-preflight-review-${round}`, {
      'x-evidence-grounding': 'true', 'x-evidence-topic': encodeHeaderValue(topic),
      'x-visual-preflight': 'true',
    });
    if (!response.ok) throw new Error(`Visual preflight provider failed (HTTP ${response.status}): ${(await response.text()).slice(0, 300)}`);
    const raw = await response.json();
    if (raw.stop_reason === 'max_tokens') throw new Error('Visual preflight review was truncated; no clearance was granted.');
    if (raw.stop_reason !== 'tool_use') throw new Error('Visual preflight provider did not complete the required review tool call.');
    const blocks = Array.isArray(raw.content) ? raw.content : [];
    const toolCalls = blocks.filter(block => block?.type === 'tool_use');
    if (toolCalls.length > 1) throw new Error('Visual preflight provider returned multiple review tool calls; no clearance was granted.');
    if (!toolCalls.length) throw new Error('Visual preflight provider omitted the required review tool call; no clearance was granted.');
    if (toolCalls[0].name !== 'submit_visual_preflight_review') {
      throw new Error(`Visual preflight provider called the wrong tool (${String(toolCalls[0].name || 'unnamed')}); no clearance was granted.`);
    }
    if (blocks.length !== 1) throw new Error('Visual preflight provider returned unexpected content alongside the review tool call.');
    return validateReview(toolCalls[0].input, story, gate.evidence);
  }

  function clinicalKey(story) {
    const copy = clone(story);
    copy.voLines.forEach(line => { delete line.visual; });
    return JSON.stringify(copy);
  }

  async function prepare(topic, original, gate, options = {}) {
    reset();
    const run = epoch;
    const active = () => {
      if (run !== epoch || (typeof options.isCurrent === 'function' && !options.isCurrent())) {
        throw new Error('Visual preflight was superseded by a newer lesson.');
      }
    };
    const local = {version: VERSION, status: 'reviewing', created_at: new Date().toISOString(),
      review_kind: 'AI source/visual risk review, not pixel certification', attempts: [], repair_count: 0,
      clinical_attempts: [], clinical_repair_count: 0, visual_repair_requests: 0, repair_failures: [], visual_preservation_reviews: [],
      expert_review: !!options.expertReview};
    report = local;
    try {
      if (options.externalFeedback != null && (typeof options.externalFeedback !== 'string' || options.externalFeedback.length > 20000)) {
        throw new Error('External audit feedback must be text of at most 20,000 characters.');
      }
      active();
      requireEvidence(original, gate);
      if (options.allowedRepairUnits != null && (!Array.isArray(options.allowedRepairUnits) ||
          !options.allowedRepairUnits.length || options.allowedRepairUnits.some(n => !original.voLines.some(line => line.n === n)))) {
        throw new Error('Preflight repair scope must contain existing anchor IDs.');
      }
      if (options.externalFeedback) local.external_feedback_sha256 = await hash(options.externalFeedback);
      let story = clone(original);
      let locked = clinicalKey(story);
      local.input_story_sha256 = await hash(key(topic, story));
      local.original_story_sha256 = local.input_story_sha256;
      active();
      for (let round = 0; round <= MAX_REPAIRS; round++) {
        active();
        const signals = inspect(story);
        if (signals.errors.length) throw new Error(signals.errors.join(' '));
        setStageDetail('prompt', `Pre-render review ${round + 1}: checking source fidelity and all ${story.voLines.length} visual relationships.`);
        let result = await review(topic, story, gate, signals, round, options.expertReview, options.externalFeedback);
        active();
        if (root.MnemorizedFirstAttempt?.isActive() && (result.clinical_status !== 'supported' ||
            result.anchors.some(row => row.status === 'repair') || result.scene?.issues?.length ||
            signals.risks.some(risk => risk.blocking))) {
          throw new Error('First-attempt preflight blocked; repairs and redesign are not permitted.');
        }
        if (result.clinical_status === 'needs_repair' && round === 0 && local.clinical_repair_count === 0) {
          if (options.allowedRepairUnits && result.clinical_findings.some(f => f.n !== null && !options.allowedRepairUnits.includes(f.n))) {
            throw new Error('Clinical findings exceed the selected anchor repair scope.');
          }
          const targets = [];
          result.clinical_findings.forEach(f => {
            const target = {anchor: f.n, field: f.field};
            if (!targets.some(t => t.anchor === target.anchor && t.field === target.field)) targets.push(target);
          });
          const before = clone(story);
          local.clinical_failure = {review: clone(result), targets: clone(targets)};
          const repaired = await repairMedicalTextFields(story, topic, targets,
            `Apply only these source-supported factual corrections, preserving all other wording and every visual association: ${JSON.stringify(result.clinical_findings)}`, !!options.expertReview, {assertActive:active});
          active();
          const expected = clone(before);
          targets.forEach(t => {
            const owner = t.anchor == null ? expected : expected.voLines.find(line => line.n === t.anchor);
            const replacement = t.anchor == null ? repaired : repaired.voLines.find(line => line.n === t.anchor);
            owner[t.field] = replacement[t.field];
          });
          if (JSON.stringify(expected) !== JSON.stringify(repaired)) throw new Error('Clinical repair changed an unselected field.');
          local.clinical_attempts.push({review: result, before_sha256: await hash(key(topic, before)),
            after_sha256: await hash(key(topic, repaired)), repairs: targets.map(t => ({...t,
              before: (t.anchor == null ? before : before.voLines[t.anchor - 1])[t.field],
              after: (t.anchor == null ? repaired : repaired.voLines[t.anchor - 1])[t.field]}))});
          active();
          local.clinical_repair_count = 1;
          delete local.clinical_failure;
          story = repaired;
          locked = clinicalKey(story);
          local.input_story_sha256 = await hash(key(topic, story));
          active();
          gate = await runMedicalQualityGate(story, story.required_concepts);
          active();
          requireEvidence(story, gate);
          result = await review(topic, story, gate, inspect(story), 'clinical-recheck', options.expertReview, options.externalFeedback);
          active();
        }
        const storyHash = await hash(key(topic, story));
        active();
        local.attempts.push({round, story_sha256: storyHash, signals, review: result});
        if (result.clinical_status !== 'supported') {
          throw new Error(`Source review ${result.clinical_status}: ${result.clinical_findings.map(f => f.issue).join(' ')}`);
        }
        if (result.anchors.some(row => row.status === 'repair' && row.repair_scope === 'redesign') ||
            result.scene.issues.some(issue => ['opening', 'association'].includes(issue.field))) {
          throw new Error('Visual encoding requires full Forge redesign; visual-only patches cannot change its opening or teaching associations.');
        }
        const affected = new Set(result.anchors.filter(row => row.status === 'repair').map(row => row.n));
        signals.risks.filter(risk => risk.blocking).forEach(risk => affected.add(risk.n));
        result.scene.issues.forEach(issue => issue.anchors.forEach(n => affected.add(n)));
        if (!affected.size) {
          local.status = 'ready';
          local.story_sha256 = storyHash;
          local.clinical_text_preserved = clinicalKey(story) === locked;
          return {story, report: clone(local)};
        }
        if (round === MAX_REPAIRS || local.visual_repair_requests >= MAX_REPAIRS) throw new Error('Visual preflight repair budget exhausted. Redesign the flagged encoding through Forge before rendering.');
        if (options.allowedRepairUnits && [...affected].some(n => !options.allowedRepairUnits.includes(n))) {
          throw new Error('Visual findings exceed the selected anchor repair scope.');
        }
        const targets = [...affected].sort((a, b) => a - b).map(n => ({anchor: n, field: 'visual'}));
        const feedback = `Independent preflight: ${JSON.stringify(result)}\nDeterministic format checks: ${JSON.stringify(signals.risks.filter(r => r.blocking))}\nChange only selected VISUAL fields. Aim for 18 words each, never over 24. Preserve the existing HOOK and narration associations. If that is impossible, retain the visual for an explicit redesign instead of inventing a different clinical meaning.`;
        let next, formatFailure = '';
        while (!next && local.visual_repair_requests < MAX_REPAIRS) {
          active();
          local.visual_repair_requests++;
          try {
            next = await repairMedicalTextFields(story, topic, targets, feedback + formatFailure, !!options.expertReview,
              {assertActive:active, onPreservationReview:value=>local.visual_preservation_reviews.push(clone(value))});
          } catch (error) {
            active();
            if (!String(error.message).startsWith('Targeted repair failed validation:')) throw error;
            local.repair_failures.push({request: local.visual_repair_requests, error: error.message});
            formatFailure = `\nPrevious patch was REJECTED and not applied: ${error.message}\nReturn substantially shorter replacement visuals, at most 18 words, preserving each load-bearing relationship.`;
            if (local.visual_repair_requests >= MAX_REPAIRS) throw error;
          }
        }
        active();
        if (clinicalKey(next) !== locked) throw new Error('Visual repair changed locked clinical text or scope.');
        if (next.voLines.some((line, i) => !affected.has(line.n) && line.visual !== story.voLines[i].visual)) {
          throw new Error('Visual repair changed an unselected anchor.');
        }
        if (next.voLines.every((line, i) => line.visual === story.voLines[i].visual)) {
          throw new Error('Visual repair made no progress. Redesign the flagged encoding through Forge.');
        }
        local.attempts[local.attempts.length - 1].repairs = targets.map(t => ({n: t.anchor,
          before: story.voLines[t.anchor - 1].visual, after: next.voLines[t.anchor - 1].visual}));
        story = next;
        local.repair_count++;
      }
    } catch (error) {
      root.MnemorizedFirstAttempt?.fail();
      local.status = 'blocked'; local.error = error.message;
      if (local.clinical_failure) local.clinical_failure.error = error.message;
      throw error;
    }
  }

  async function bind(topic, story, pair) {
    const run = epoch, approved = report;
    const storyHash = await hash(key(topic, story)), promptHash = await hash(pair.prompt2);
    if (run !== epoch || approved?.status !== 'ready' || approved.story_sha256 !== storyHash) throw new Error('Preflight story changed before prompt binding.');
    approved.prompt_sha256 = promptHash;
    binding = {story: key(topic, story), prompt1: pair.prompt1, prompt2: pair.prompt2};
  }
  function assertReady(topic, story, prompt1, prompt2) {
    if (report?.status !== 'ready' || !binding || binding.story !== key(topic, story) ||
        binding.prompt1 !== String(prompt1 || '').trim() || binding.prompt2 !== String(prompt2 || '').trim()) {
      throw new Error('Image preflight is missing or stale. Rebuild the current lesson prompts before rendering.');
    }
  }
  root.MnemorizedVisualPreflight = {VERSION, inspect, parseReview, validateReview, requireEvidence, clinicalKey,
    prepare, bind, assertReady, reset, invalidate, getReport: () => report ? clone(report) : null};
})(window);
