// ══════════════════════════════════════════════════
// FORGE LESSON SPEC — Learning Object Ontology / Lesson Blueprint
// Loaded after forge-state.js, before forge-input-builder.js.
//
// Purpose: turn the guided input builder's fields into a STRUCTURED lesson spec
// that survives into generation (Stage 1 scope contract) and the medical quality
// gate (independent anchor contract). Without this, the builder's archetype,
// must-include, and constraints are flattened into the opaque #topic string and
// nothing downstream enforces them — so the quality gate ends up grading the
// generation against its own anchors instead of an upstream contract.
// ══════════════════════════════════════════════════

// Each archetype declares what a lesson of that kind is OBLIGATED to teach,
// what is out of scope by default, and how anchors should be shaped. These
// required categories become the backbone of the anchor contract.
const LESSON_ARCHETYPES = {
  condition: {
    label: 'Condition',
    requiredCategories: [
      'Diagnostic criteria and key thresholds',
      'Classic presentation and core pathophysiology',
      'First-line management with exact doses and timing',
      'Complications, contraindications, and common pitfalls',
      'Disposition or resolution criteria',
    ],
    outOfScopeDefaults: [
      'Exhaustive differential taxonomy unless the topic asks for it',
      'Unrelated chronic or outpatient management',
    ],
    anchorGuidance: 'Cluster labs/thresholds, management steps, and safety pitfalls into distinct spatial zones.',
  },
  'drug-class': {
    label: 'Drug Class',
    requiredCategories: [
      'Mechanism of action',
      'Major indications and preferred use cases',
      'High-yield adverse effects and toxicities',
      'Contraindications, monitoring, and key interactions',
      'Black-box or life-threatening warnings',
    ],
    outOfScopeDefaults: [
      'Full pharmacokinetic derivations unless requested',
      'Non-representative niche agents outside the class',
    ],
    anchorGuidance: 'Separate similar drugs when side effects or indications differ; encode receptor/enzyme targets by shape.',
  },
  algorithm: {
    label: 'Algorithm / Protocol',
    requiredCategories: [
      'Entry criteria and immediate stabilization steps',
      'Ordered decision points in sequence',
      'Medication/procedure doses, timing, and reassessment points',
      'Stopping criteria and disposition',
      'Failure/escalation pathway and refractory options',
    ],
    outOfScopeDefaults: [
      'Broad disease etiology and taxonomy unless requested',
      'Non-emergent chronic workup',
    ],
    anchorGuidance: 'Keep the sequence explicit and left-to-right; do not merge steps with different thresholds or timing.',
  },
  differential: {
    label: 'Differential',
    requiredCategories: [
      'Key discriminating symptoms and exam findings',
      'First tests and confirmatory tests',
      'Red flags and do-not-miss diagnoses',
      'Initial management differences between look-alikes',
      'Test-interpretation pitfalls',
    ],
    outOfScopeDefaults: [
      'Full management chapters for each diagnosis',
      'Rare zebras unless the topic is specifically about them',
    ],
    anchorGuidance: 'Use contrastive anchors so similar diagnoses do not blur together; prioritize dangerous mimics.',
  },
  anatomy: {
    label: 'Anatomy',
    requiredCategories: [
      'Spatial relationships and pathway/order',
      'Function of each major structure',
      'Lesion signs, deficits, or referred-pain patterns',
      'Blood supply, innervation, or embryology when high-yield',
    ],
    outOfScopeDefaults: [
      'Unrelated systemic disease management',
      'Histology-level detail unless requested',
    ],
    anchorGuidance: 'Make the spatial route explicit; use laterality, levels, and named branches precisely.',
  },
};

function getLessonArchetype(id) {
  return LESSON_ARCHETYPES[id] || LESSON_ARCHETYPES.condition;
}

function domFieldValue(id) {
  return String(document.getElementById(id)?.value || '').trim();
}

function domFieldLines(id) {
  return String(document.getElementById(id)?.value || '')
    .split('\n')
    .map(line => line.trim().replace(/^[-*•]\s*/, ''))
    .filter(Boolean);
}

// Rebuild the lesson spec from the guided input builder's DOM fields. The builder
// stamps the active archetype onto the #topic dataset when it drafts, so this
// module can reconstruct the structured blueprint without the builder widget
// depending on the rest of the app. Returns null when no builder draft is active.
function readLessonSpecFromDom() {
  const topicField = document.getElementById('topic');
  const archetypeId = topicField?.dataset?.builderPreset;
  if (!archetypeId) return null;
  return buildLessonSpec(archetypeId, {
    topic: topicField?.dataset?.builderTopic || domFieldValue('builder-topic'),
    learner: domFieldValue('builder-learner'),
    goal: domFieldValue('builder-goal'),
    source: domFieldValue('builder-source'),
    mustInclude: domFieldLines('builder-must-include'),
    constraints: domFieldLines('builder-constraints'),
  });
}

// Build a structured spec from the builder DOM fields + the active archetype.
// `mustEncode` is the union of the user's must-include lines and the archetype's
// required categories — this is the backbone of the downstream anchor contract.
function buildLessonSpec(archetypeId, fields) {
  const archetype = getLessonArchetype(archetypeId);
  const f = fields || {};
  const builderTopic = String(f.topic || '').trim();
  if (!builderTopic) return null;

  const userMust = Array.isArray(f.mustInclude) ? f.mustInclude.filter(Boolean) : [];
  const constraints = Array.isArray(f.constraints) ? f.constraints.filter(Boolean) : [];

  // De-duplicate case-insensitively while preserving order and original casing.
  const seen = new Set();
  const mustEncode = [];
  [...userMust, ...archetype.requiredCategories].forEach(item => {
    const key = String(item).toLowerCase().replace(/\s+/g, ' ').trim();
    if (!key || seen.has(key)) return;
    seen.add(key);
    mustEncode.push(String(item).trim());
  });

  return {
    archetype: archetypeId in LESSON_ARCHETYPES ? archetypeId : 'condition',
    archetypeLabel: archetype.label,
    builderTopic,
    learner: String(f.learner || '').trim() || 'Medical learner',
    goal: String(f.goal || '').trim(),
    sourceType: String(f.source || '').trim(),
    mustEncode,
    constraints,
    outOfScope: archetype.outOfScopeDefaults.slice(),
    anchorGuidance: archetype.anchorGuidance,
    createdAt: Date.now(),
  };
}

// Return the spec only if it is still relevant to the current topic text, so a
// stale blueprint (e.g. drafted for DKA, then the user retyped a different topic)
// is not silently applied. Relevance = the drafted builder topic still appears in
// the Section I box.
function getActiveLessonSpec(topicText) {
  const spec = readLessonSpecFromDom();
  if (!spec) return null;
  const haystack = String(topicText || '').toLowerCase();
  const needle = String(spec.builderTopic || '').toLowerCase();
  if (!needle) return null;
  return haystack.includes(needle) ? spec : null;
}

// Human-readable blueprint block injected into the Stage 1 clinical-context prompt
// so generation receives an explicit scope + coverage contract, not just prose.
function lessonSpecToPromptText(spec) {
  if (!spec) return '';
  const lines = [
    'LESSON BLUEPRINT — treat this as the binding scope and coverage contract for this lesson:',
    `- Learning object type: ${spec.archetypeLabel}`,
    `- Target learner: ${spec.learner}`,
  ];
  if (spec.goal) lines.push(`- Learning goal: ${spec.goal}`);
  if (spec.sourceType) lines.push(`- Source basis: ${spec.sourceType}`);
  if (spec.mustEncode.length) {
    lines.push('- MUST cover every one of these categories (each becomes at least one anchor):');
    spec.mustEncode.forEach(item => lines.push(`    • ${item}`));
  }
  if (spec.constraints.length) {
    lines.push('- Accuracy constraints:');
    spec.constraints.forEach(item => lines.push(`    • ${item}`));
  }
  if (spec.outOfScope.length) {
    lines.push('- Out of scope unless the topic explicitly asks for it (do NOT pad the scene with these):');
    spec.outOfScope.forEach(item => lines.push(`    • ${item}`));
  }
  lines.push(`- Anchor guidance: ${spec.anchorGuidance}`);
  return lines.join('\n');
}

// The independent anchor contract handed to the medical quality gate. Merges the
// blueprint's required categories with the Stage 1 core concepts so the gate
// checks generation against upstream obligations, not against its own anchors.
function buildAnchorContract(spec, coreConcepts) {
  const seen = new Set();
  const contract = [];
  const push = (item) => {
    const text = String(item || '').trim();
    const key = text.toLowerCase().replace(/\s+/g, ' ');
    if (!text || seen.has(key)) return;
    seen.add(key);
    contract.push(text);
  };
  (spec?.mustEncode || []).forEach(push);
  (coreConcepts || []).forEach(push);
  return contract.slice(0, 16);
}

if (typeof window !== 'undefined') {
  window.MnemorizedLessonSpec = {
    LESSON_ARCHETYPES,
    buildLessonSpec,
    readLessonSpecFromDom,
    getActiveLessonSpec,
    lessonSpecToPromptText,
    buildAnchorContract,
  };
}
