// Guided input builder for Section I.
// Writes into the existing #topic textarea so the generation pipeline stays unchanged.

const INPUT_BUILDER_PRESETS = {
  condition: {
    goal: 'diagnose, manage, and avoid dangerous pitfalls',
    mustInclude: [
      'Diagnostic criteria and key thresholds',
      'Pathophysiology and classic presentation',
      'Initial workup and first-line management',
      'Complications, contraindications, and common test traps',
    ],
    constraints: [
      'Preserve exact numbers, cutoffs, doses, and timing.',
      'Include severe variants and life-threatening exceptions.',
      'Group related facts into 8-10 visual anchors without omitting major categories.',
    ],
  },
  'drug-class': {
    goal: 'remember mechanism, indications, adverse effects, and contraindications',
    mustInclude: [
      'Mechanism of action',
      'Major indications and preferred use cases',
      'High-yield adverse effects and toxicities',
      'Contraindications, monitoring, and interactions',
    ],
    constraints: [
      'Separate similar drugs when their side effects or indications differ.',
      'Use exact receptor, enzyme, electrolyte, or dosing details when relevant.',
      'Include black-box or life-threatening adverse effects.',
    ],
  },
  algorithm: {
    goal: 'execute the protocol step-by-step without skipping safety checks',
    mustInclude: [
      'Entry criteria and immediate stabilization steps',
      'Decision points in order',
      'Medication/procedure doses, timing, and reassessment points',
      'Stopping criteria, disposition, and failure/escalation pathway',
    ],
    constraints: [
      'Keep the sequence explicit and left-to-right.',
      'Do not merge steps that have different thresholds or timing.',
      'Highlight safety checks before irreversible or high-risk actions.',
    ],
  },
  differential: {
    goal: 'distinguish look-alike diagnoses quickly',
    mustInclude: [
      'Key discriminating symptoms and exam findings',
      'First tests and confirmatory tests',
      'Red flags and do-not-miss diagnoses',
      'Initial management differences',
    ],
    constraints: [
      'Use contrastive anchors so similar diagnoses do not blur together.',
      'Prioritize dangerous mimics and time-sensitive decisions.',
      'Include test interpretation pitfalls.',
    ],
  },
  anatomy: {
    goal: 'map structure, function, lesion patterns, and clinical correlations',
    mustInclude: [
      'Spatial relationships and pathway/order',
      'Function of each major structure',
      'Lesion signs, deficits, or referred pain patterns',
      'Blood supply, innervation, or embryology if high-yield',
    ],
    constraints: [
      'Make the spatial route explicit in the memory palace.',
      'Do not skip small structures if they are commonly tested.',
      'Use laterality, levels, and named branches precisely.',
    ],
  },
};

let activeInputBuilderPreset = 'condition';

function setBuilderStatus(message, tone) {
  const el = document.getElementById('builder-status');
  if (!el) return;
  el.textContent = message;
  el.style.color = tone === 'error' ? 'var(--red)' : tone === 'success' ? 'var(--acid)' : 'var(--muted)';
}

function selectBuilderPreset(preset) {
  if (!INPUT_BUILDER_PRESETS[preset]) return;
  activeInputBuilderPreset = preset;
  document.querySelectorAll('[data-builder-preset]').forEach(button => {
    button.classList.toggle('active', button.dataset.builderPreset === preset);
  });

  const selected = INPUT_BUILDER_PRESETS[preset];
  const goal = document.getElementById('builder-goal');
  const mustInclude = document.getElementById('builder-must-include');
  const constraints = document.getElementById('builder-constraints');
  if (goal) goal.value = selected.goal;
  if (mustInclude) mustInclude.value = selected.mustInclude.join('\n');
  if (constraints) constraints.value = selected.constraints.join('\n');
  setBuilderStatus('Preset loaded. Edit anything, then draft it into the text box.', 'success');
}

function builderValue(id) {
  return (document.getElementById(id)?.value || '').trim();
}

function normalizeBuilderLines(raw) {
  return String(raw || '')
    .split('\n')
    .map(line => line.trim().replace(/^[-*\u2022]\s*/, ''))
    .filter(Boolean);
}

function formatBulletBlock(label, lines) {
  if (!lines.length) return '';
  return `${label}:\n${lines.map(line => `- ${line}`).join('\n')}`;
}

function buildGuidedTopicText() {
  const topic = builderValue('builder-topic');
  const learner = builderValue('builder-learner');
  const goal = builderValue('builder-goal');
  const source = builderValue('builder-source');
  const mustInclude = normalizeBuilderLines(builderValue('builder-must-include'));
  const constraints = normalizeBuilderLines(builderValue('builder-constraints'));

  if (!topic) {
    throw new Error('Add a topic first.');
  }

  const blocks = [
    `Topic: ${topic}`,
    `Learner: ${learner || 'Medical learner'}`,
    `Learning goal: ${goal || INPUT_BUILDER_PRESETS[activeInputBuilderPreset].goal}`,
    `Source type: ${source || 'Educational/source material only'}`,
    'Privacy: Do not include patient-identifying information.',
    formatBulletBlock('Must encode', mustInclude),
    formatBulletBlock('Accuracy constraints', constraints),
    'Output expectation: Create a premium visual memory palace with 8-10 anchors, a concise rapid review script, exact medical facts, and no unsupported patient-specific assumptions.',
  ];

  return blocks.filter(Boolean).join('\n\n');
}

function draftGuidedTopic(mode) {
  const topicField = document.getElementById('topic');
  if (!topicField) return;

  let draft = '';
  try {
    draft = buildGuidedTopicText();
  } catch (error) {
    setBuilderStatus(error.message, 'error');
    document.getElementById('builder-topic')?.focus();
    return;
  }

  const existing = topicField.value.trim();
  const shouldAppend = mode === 'append';
  if (existing && !shouldAppend && !confirm('Replace the current Section I text with this guided brief?')) {
    setBuilderStatus('Kept the existing text box content.');
    return;
  }

  topicField.value = shouldAppend && existing
    ? `${existing}\n\nAdditional generation requirements:\n${draft}`
    : draft;
  topicField.dispatchEvent(new Event('input', { bubbles: true }));
  topicField.focus();
  setBuilderStatus(shouldAppend ? 'Requirements appended to Section I.' : 'Guided brief drafted into Section I.', 'success');
}

function clearGuidedBuilder() {
  [
    'builder-topic',
    'builder-goal',
    'builder-must-include',
    'builder-constraints',
  ].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  selectBuilderPreset(activeInputBuilderPreset);
  setBuilderStatus('Builder cleared and preset defaults restored.');
}

selectBuilderPreset(activeInputBuilderPreset);
