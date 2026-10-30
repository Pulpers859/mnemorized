"""Offline first-attempt guards using real Forge code and nonclinical fixtures."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node is required for Forge VM tests")

RUNNER = r"""
const fs = require('fs');
const vm = require('vm');
const {webcrypto} = require('crypto');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const elements = {};
const element = id => elements[id] ||= {
  value: '', textContent: '', innerHTML: '', disabled: false, style: {},
  addEventListener() {}, classList: {add() {}, remove() {}}
};
const context = vm.createContext({
  crypto: webcrypto, TextEncoder, URLSearchParams, Response,
  input: input.data, console: {info() {}, warn() {}, error() {}},
  document: {getElementById: element},
  MnemorizedUtils: {getApiUrl: path => path, escapeHtml: text => text,
    runSupabaseQuery() {}, getApiBase: () => ''}
});
vm.runInContext(`
window = globalThis;
window.location = {origin: 'https://offline.invalid', search: ''};
const clone = value => JSON.parse(JSON.stringify(value));
const topic = 'Workshop objects';
document.getElementById('topic').value = topic;
const authState = {session: null};
const appConfig = {};
const requests = [], replies = [], repairs = [], gateChecks = [];
fetch = async (url, options) => {
  if (url === '/api/health') return new Response(JSON.stringify({
    anthropic_configured: true, gemini_configured: true,
    medical_knowledge_configured: true, provider_auth_ready: true
  }));
  if (url !== '/api/anthropic/messages') throw new Error('Unexpected offline URL: ' + url);
  requests.push({url, body: JSON.parse(options.body), headers: clone(options.headers)});
  const reply = replies.shift() || {};
  if (reply.throw) throw new Error(reply.throw);
  return new Response(reply.raw === undefined
    ? JSON.stringify(reply.body || {stop_reason: 'end_turn', content: []}) : reply.raw,
    {status: reply.status || 200, headers: {'Content-Type': 'application/json'}});
};
async function rejected(fn) {
  try {await fn(); return null;} catch (error) {return error.message;}
}
function errorOf(fn) {
  try {fn(); return null;} catch (error) {return error.message;}
}
`, context);
vm.runInContext(fs.readFileSync('frontend/scripts/forge-state.js', 'utf8'), context);
vm.runInContext(fs.readFileSync('frontend/scripts/forge-story-contract.js', 'utf8'), context);
vm.runInContext(`
backendState = {checked: true, reachable: true, configured: true,
  geminiConfigured: true, medicalKnowledgeConfigured: true, providerAuthReady: true};
const api = window.MnemorizedFirstAttempt;
if (!api) throw new Error('MnemorizedFirstAttempt interface has not landed');
const stages = ['stage1-clinical-context', 'medical-contract-source-review',
  'stage2-story-script-compact', 'visual-preflight-review-0'];
const configuration = {arm: 'baseline', topicId: 'workshop-01', topic};
function configure(overrides = {}) {return api.configure({...configuration, ...overrides});}
function body(overrides = {}) {
  return {model: CLAUDE_MODEL, max_tokens: 2600,
    system: 'Describe ordinary workshop objects.',
    messages: [{role: 'user', content: topic}], ...overrides};
}
async function advance(count = 3) {
  for (let index = 0; index < count; index++) await claudeFetch(body(), stages[index]);
}
`, context);
if (input.preflight) {
  vm.runInContext(`
const story = {
  scene_title: 'Workshop', opening: 'An open workshop with bare walls.',
  required_concepts: ['The vase rests on its stand.', 'The kite hangs from its hook.'],
  review_script: 'Recall the stand and the hook.',
  voLines: [
    {n: 1, visual: 'A blue vase rests on a broad stand.', hook: 'spatial: supported vase',
      narration: 'The vase rests on its stand.', anchor: 'Vase on stand'},
    {n: 2, visual: 'A red kite hangs from a wall hook.', hook: 'spatial: suspended kite',
      narration: 'The kite hangs from its hook.', anchor: 'Kite on hook'}
  ]
};
const gate = {verdict: 'ready_for_review', evidence_status: 'matched',
  evidence: [{source_key: 'workshop-reference', page_start: 1}],
  missing_from_generation: [], ungrounded_concepts: []};
function setStageDetail() {}
async function repairMedicalTextFields(source, requestedTopic, targets) {
  repairs.push(clone(source));
  const next = clone(source);
  for (const target of targets) {
    const owner = target.anchor == null ? next : next.voLines.find(line => line.n === target.anchor);
    owner[target.field] += ' Clear spacing.';
  }
  return next;
}
async function runMedicalQualityGate(source) {
  gateChecks.push(clone(source)); return clone(gate);
}
function makeReview(needsRepair = false) {
  return {clinical_status: 'supported', clinical_findings: [],
    anchors: story.voLines.map((line, index) => ({n: line.n,
      status: needsRepair && index === 0 ? 'repair' : 'ready', repair_scope: 'visual',
      relationship_quote: line.visual, why: 'The object has explicit support.',
      source_refs: clone(gate.evidence),
      risks: needsRepair && index === 0 ? ['Separate the support silhouette.'] : []})),
    scene: {status: 'ready', issues: []}};
}
function reviewResponse(value = makeReview(), stop = 'tool_use') {
  return {stop_reason: stop, content: [{type: 'tool_use',
    name: 'submit_visual_preflight_review', input: value}]};
}
`, context);
  vm.runInContext(fs.readFileSync('frontend/scripts/forge-visual-preflight.js', 'utf8'), context);
}
if (input.pipeline) {
  const source = fs.readFileSync('frontend/scripts/forge-pipeline.js', 'utf8');
  const end = source.indexOf('function renderImagePromptPair(');
  if (end < 0) throw new Error('Prompt builder boundary changed');
  vm.runInContext(source.slice(0, end), context);
  const templateStart = source.indexOf('const compactStorySystem =');
  const templateEnd = source.indexOf('const denseProtocol =', templateStart);
  const attemptsEnd = source.indexOf('let storyValidation =', templateEnd);
  if (templateStart < 0 || templateEnd < templateStart || attemptsEnd < templateEnd) {
    throw new Error('Story template or attempt boundary changed');
  }
  context.storyTemplate = source.slice(templateStart, templateEnd);
  context.storyAttemptsSource = source.slice(templateEnd, attemptsEnd);
  vm.runInContext(`
const clinicalContext = 'SOURCE FIXTURE: the vase rests on the stand.\\nCOVERAGE FIXTURE: preserve all eight ordinary-object units.';
function actualStorySystem() {return eval(storyTemplate + '\\ncompactStorySystem;');}
function actualStoryAttempts(dense) {
  const coreConcepts = ['Vase on stand', 'Kite on hook'];
  const compactStorySystem = actualStorySystem(), storyUser = 'Workshop fixture';
  const isDenseProtocolTopic = () => dense;
  return eval(storyAttemptsSource + '\\nstoryAttempts;');
}
`, context);
}
Promise.resolve(vm.runInContext(input.expression, context)).then(
  result => process.stdout.write(JSON.stringify(result)),
  error => {console.error(error); process.exitCode = 1;}
);
"""


def evaluate(expression, data=None, *, preflight=False, pipeline=False):
    result = subprocess.run(
        [NODE, "-e", RUNNER], cwd=ROOT,
        input=json.dumps({"expression": expression, "data": data,
                          "preflight": preflight, "pipeline": pipeline}),
        text=True, encoding="utf-8", capture_output=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_profile_is_explicit_and_default_wrapper_is_unchanged():
    result = evaluate("""(async () => {
      const active = api.isActive();
      const original = body({model: CLAUDE_ADVISOR_MODEL, max_tokens: 9000,
        tools: [{name: 'advisor'}], betas: ['normal-beta']});
      for (let index = 0; index < 5; index++) await claudeFetch(original, 'normal-stage');
      return {active, original, requests, library: api.metaphorLibrary('Unchanged text.')};
    })()""")
    assert result["active"] is False
    assert len(result["requests"]) == 5
    assert all(request["body"] == result["original"] for request in result["requests"])
    assert all("x-forge-first-attempt" not in request["headers"] for request in result["requests"])
    assert result["library"] == "Unchanged text."


@pytest.mark.parametrize("arm", ["baseline", "candidate"])
def test_profile_cannot_be_reconfigured_or_reset(arm):
    result = evaluate("""(() => {
      configure({arm: input});
      const before = clone(api.snapshot());
      const error = errorOf(() => configure({arm: input === 'baseline' ? 'candidate' : 'baseline',
        topicId: 'workshop-02', topic: 'Other workshop'}));
      return {error, before, after: api.snapshot(), resetExposed: typeof api.reset === 'function'};
    })()""", arm)
    assert result["error"]
    assert result["before"] == result["after"]
    assert result["resetExposed"] is False


def test_snapshot_mutation_cannot_change_bound_topic_or_arm():
    result = evaluate("""(async () => {
      configure();
      const before = clone(api.snapshot());
      const exposed = api.snapshot();
      try {exposed.arm = 'candidate'; exposed.topic = 'Other workshop';
        exposed.topicId = 'workshop-02'; exposed.requests = [];} catch (_) {}
      const after = clone(api.snapshot());
      await claudeFetch(body(), stages[0]);
      return {before, after, requests};
    })()""")
    assert result["before"] == result["after"]
    assert len(result["requests"]) == 1


def test_snapshot_request_records_are_defensive_copies():
    result = evaluate("""(async () => {
      configure(); await advance(1);
      const before = clone(api.snapshot()), exposed = api.snapshot();
      try {exposed.requests[0].stage = 'other-stage'; exposed.requests[0].max_tokens = 9000;
        exposed.requests.push({stage: 'extra-stage'});} catch (_) {}
      return {before, after: api.snapshot()};
    })()""")
    assert result["before"] == result["after"]


def test_explicit_fail_is_terminal_even_before_the_first_dispatch():
    result = evaluate("""(async () => {
      configure(); api.fail();
      const error = await rejected(() => claudeFetch(body(), stages[0]));
      return {error, requests, snapshot: api.snapshot()};
    })()""")
    assert result["error"] and result["requests"] == []
    assert result["snapshot"]["blocked"] is True


@pytest.mark.parametrize("arm", ["baseline", "candidate"])
def test_ablation_changes_exactly_one_catalog_row(arm):
    result = evaluate("""(() => {
      configure({arm: input});
      return {original: VISUAL_METAPHOR_LIBRARY,
        selected: api.metaphorLibrary(VISUAL_METAPHOR_LIBRARY)};
    })()""", arm, pipeline=True)
    original = result["original"]
    row = [line for line in original.splitlines() if line.startswith("- Body systems (setting-level):")]
    assert len(row) == 1
    expected = original if arm == "baseline" else "\n".join(
        line for line in original.splitlines() if line != row[0]
    )
    assert result["selected"] == expected


@pytest.mark.parametrize("arm", ["baseline", "candidate"])
def test_actual_wrapper_enforces_four_stages_and_adds_bound_headers(arm):
    result = evaluate("""(async () => {
      configure({arm: input});
      const maxima = [2600, 2600, 6144, 5000];
      const originals = stages.map((stage, index) => body({max_tokens: maxima[index]}));
      for (let index = 0; index < stages.length; index++) {
        const response = await claudeFetch(originals[index], stages[index], {
          'x-research-arm': 'spoofed', 'x-research-topic-id': 'spoofed',
          'x-research-stage': 'spoofed', 'x-forge-first-attempt': 'spoofed'});
        await response.json();
      }
      const finished = api.snapshot();
      const error = await rejected(() => claudeFetch(body(), stages[0]));
      return {originals, finished, error, requests, blocked: api.snapshot()};
    })()""", arm)
    assert len(result["requests"]) == 4
    assert result["finished"]["blocked"] is False
    assert result["error"] and result["blocked"]["blocked"] is True
    assert result["finished"]["requests"] == [
        {"stage": stage, "model": "claude-sonnet-4-6", "max_tokens": maximum}
        for stage, maximum in zip(
            ["stage1-clinical-context", "medical-contract-source-review",
             "stage2-story-script-compact", "visual-preflight-review-0"],
            [2600, 2600, 6144, 5000], strict=True,
        )
    ]
    for request, original, stage in zip(
        result["requests"], result["originals"], result["finished"]["requests"], strict=True,
    ):
        assert request["body"] == original
        assert request["headers"]["x-forge-first-attempt"] == "v1"
        assert request["headers"]["x-research-arm"] == arm
        assert request["headers"]["x-research-topic-id"] == "workshop-01"
        assert request["headers"]["x-research-stage"] == stage["stage"]


@pytest.mark.parametrize("overrides", [
    {"model": "claude-opus-4-8"}, {"model": None},
    {"max_tokens": 6145}, {"max_tokens": 0}, {"max_tokens": -1},
    {"max_tokens": 1.5}, {"max_tokens": "6144"}, {"max_tokens": None},
    {"betas": ["advisor-tool-2026-03-01"]},
    {"tools": [{"name": "advisor", "type": "advisor_20260301", "model": "claude-opus-4-8"}]},
    {"tools": [{"name": "submit_visual_preflight_review", "type": "advisor_20260301"}]},
    {"tools": [{"name": "unexpected_tool"}]},
])
def test_invalid_request_is_blocked_before_transport_and_remains_terminal(overrides):
    result = evaluate("""(async () => {
      configure();
      const error = await rejected(() => claudeFetch(body(input), stages[0]));
      const again = await rejected(() => claudeFetch(body(), stages[0]));
      return {error, again, requests, snapshot: api.snapshot()};
    })()""", overrides)
    assert result["error"] and result["again"]
    assert result["requests"] == result["snapshot"]["requests"] == []
    assert result["snapshot"]["blocked"] is True


@pytest.mark.parametrize("stage", ["medical-contract-source-review", "unknown", "", None])
def test_out_of_order_or_unknown_stage_cannot_be_corrected_into_a_new_attempt(stage):
    result = evaluate("""(async () => {
      configure();
      const error = await rejected(() => claudeFetch(body(), input));
      const again = await rejected(() => claudeFetch(body(), stages[0]));
      return {error, again, requests, snapshot: api.snapshot()};
    })()""", stage)
    assert result["error"] and result["again"]
    assert result["requests"] == []
    assert result["snapshot"]["blocked"] is True


def test_duplicate_stage_cannot_be_retried_or_followed_by_next_stage():
    result = evaluate("""(async () => {
      configure(); await advance(1);
      const error = await rejected(() => claudeFetch(body(), stages[0]));
      const next = await rejected(() => claudeFetch(body(), stages[1]));
      return {error, next, requests, snapshot: api.snapshot()};
    })()""")
    assert result["error"] and result["next"]
    assert len(result["requests"]) == len(result["snapshot"]["requests"]) == 1
    assert result["snapshot"]["blocked"] is True


def test_changed_topic_remains_terminal_after_restoring_original_topic():
    result = evaluate("""(async () => {
      configure(); document.getElementById('topic').value = 'Other workshop';
      const error = await rejected(() => claudeFetch(body(), stages[0]));
      document.getElementById('topic').value = topic;
      const restored = await rejected(() => claudeFetch(body(), stages[0]));
      return {error, restored, requests, snapshot: api.snapshot()};
    })()""")
    assert result["error"] and result["restored"]
    assert result["requests"] == [] and result["snapshot"]["blocked"] is True


@pytest.mark.parametrize("reply", [
    {"status": status} for status in [401, 402, 429, 500, 502, 503, 504]
] + [
    {"throw": "Offline transport failure"}, {"raw": "not JSON"},
    {"body": {"stop_reason": "max_tokens", "content": []}},
])
def test_wrapper_failure_is_terminal_without_refund_retry_or_reconfigure(reply):
    result = evaluate("""(async () => {
      configure(); replies.push(input);
      const error = await rejected(() => claudeFetch(body(), stages[0]));
      const failed = api.snapshot();
      const same = await rejected(() => claudeFetch(body(), stages[0]));
      const next = await rejected(() => claudeFetch(body(), stages[1]));
      const reconfigure = errorOf(() => configure());
      return {error, failed, same, next, reconfigure, requests, final: api.snapshot()};
    })()""", reply)
    assert all(result[name] for name in ["error", "same", "next", "reconfigure"])
    assert len(result["requests"]) == len(result["failed"]["requests"]) == 1
    assert result["failed"]["blocked"] is True
    assert result["final"] == result["failed"]


@pytest.mark.parametrize("header", ["anthropic-beta", "Anthropic-Beta"])
def test_beta_headers_are_rejected_before_transport(header):
    result = evaluate("""(async () => {
      configure();
      const error = await rejected(() => claudeFetch(body(), stages[0], {[input]: 'advisor-tool-2026-03-01'}));
      return {error, requests, snapshot: api.snapshot()};
    })()""", header)
    assert result["error"]
    assert result["requests"] == []
    assert result["snapshot"]["blocked"] is True


def test_actual_story_template_ablation_preserves_source_coverage_and_every_other_character():
    result = evaluate("""(() => {
      const inactive = actualStorySystem();
      configure({arm: input});
      return {inactive, active: actualStorySystem(), coverage: clinicalContext,
        library: VISUAL_METAPHOR_LIBRARY};
    })()""", "candidate", pipeline=True)
    row = next(line for line in result["library"].splitlines()
               if line.startswith("- Body systems (setting-level):"))
    assert result["inactive"].count(row) == 1
    assert result["active"] == result["inactive"].replace(row + "\n", "", 1)
    assert result["coverage"] in result["active"]


def test_actual_story_template_baseline_is_byte_identical_to_disabled_profile():
    result = evaluate("""(() => {
      const inactive = actualStorySystem(); configure();
      return {inactive, active: actualStorySystem()};
    })()""", pipeline=True)
    assert result["active"] == result["inactive"]


@pytest.mark.parametrize("dense", [False, True])
@pytest.mark.parametrize("arm", [None, "baseline", "candidate"])
def test_actual_story_attempt_construction_is_single_only_when_profile_active(arm, dense):
    result = evaluate("""(() => {
      if (input.arm) configure({arm: input.arm});
      return actualStoryAttempts(input.dense);
    })()""", {"arm": arm, "dense": dense}, pipeline=True)
    expected = ["compact"] if arm else (
        ["dense-compact", "dense-compact-strict", "dense-visual-hard-gate"] if dense
        else ["compact", "compact-strict", "visual-hard-gate"]
    )
    assert [attempt["label"] for attempt in result] == expected
    for attempt in result:
        assert attempt["body"]["max_tokens"] == 6144
        assert attempt["body"]["model"] == "claude-sonnet-4-6"
        assert attempt["body"]["tools"][0]["name"] == "submit_memory_palace"
        assert attempt["body"]["tools"][0]["strict"] is True
        assert "betas" not in attempt["body"]


@pytest.mark.parametrize("failure", ["visual", "clinical", "truncated"])
def test_actual_preflight_failure_is_terminal_before_helpers_and_reset_cannot_refund(failure):
    result = evaluate("""(async () => {
      configure(); await advance();
      let value = makeReview(input === 'visual');
      if (input === 'clinical') value = {clinical_status: 'needs_repair',
        clinical_findings: [{n: 1, field: 'narration', quote: story.voLines[0].narration,
          issue: 'Clarify the support relationship.', source_refs: clone(gate.evidence)}],
        anchors: [], scene: null};
      replies.push({body: reviewResponse(value, input === 'truncated' ? 'max_tokens' : 'tool_use')});
      const error = await rejected(() => window.MnemorizedVisualPreflight.prepare(topic, story, gate));
      const failed = api.snapshot(), report = window.MnemorizedVisualPreflight.getReport();
      window.MnemorizedVisualPreflight.reset();
      const again = await rejected(() => window.MnemorizedVisualPreflight.prepare(topic, story, gate));
      const reconfigure = errorOf(() => configure({topicId: 'workshop-02'}));
      return {error, again, reconfigure, failed, report, requests, repairs, gateChecks,
        final: api.snapshot()};
    })()""", failure, preflight=True)
    assert result["error"] and result["again"] and result["reconfigure"]
    assert len(result["requests"]) == len(result["failed"]["requests"]) == 4
    assert result["repairs"] == result["gateChecks"] == []
    assert result["report"]["status"] == "blocked"
    assert result["failed"]["blocked"] is True
    assert result["final"] == result["failed"]


def test_clean_actual_preflight_is_the_fourth_sonnet_call_without_advisor():
    result = evaluate("""(async () => {
      configure(); await advance(); replies.push({body: reviewResponse()});
      const before = JSON.stringify(story);
      const prepared = await window.MnemorizedVisualPreflight.prepare(topic, story, gate);
      return {unchanged: JSON.stringify(prepared.story) === before,
        report: prepared.report, snapshot: api.snapshot(), requests, repairs, gateChecks};
    })()""", preflight=True)
    assert result["unchanged"]
    assert result["report"]["status"] == "ready"
    assert result["snapshot"]["blocked"] is False
    assert len(result["requests"]) == 4
    assert result["repairs"] == result["gateChecks"] == []
    review = result["requests"][-1]["body"]
    assert review["model"] == "claude-sonnet-4-6" and review["max_tokens"] == 5000
    assert "betas" not in review
    assert [tool["name"] for tool in review["tools"]] == ["submit_visual_preflight_review"]


def test_disabled_profile_keeps_normal_preflight_repair_behavior():
    result = evaluate("""(async () => {
      replies.push({body: reviewResponse(makeReview(true))}, {body: reviewResponse()});
      const prepared = await window.MnemorizedVisualPreflight.prepare(topic, story, gate);
      return {report: prepared.report, requests, repairs, snapshot: api.snapshot()};
    })()""", preflight=True)
    assert result["snapshot"] is None
    assert result["report"]["status"] == "ready"
    assert len(result["requests"]) == 2 and len(result["repairs"]) == 1


def test_actual_gemini_director_is_blocked_before_transport_and_marks_profile_terminal():
    result = evaluate("""(async () => {
      configure();
      let transportCalls = 0;
      const originalFetch = fetch;
      fetch = (...args) => {transportCalls++; return originalFetch(...args);};
      const error = await rejected(() => geminiPromptDirectorFetch(
        {topic, anchors: []}, 'alternate-director'));
      const failed = api.snapshot();
      const next = await rejected(() => claudeFetch(body(), stages[0]));
      return {error, next, transportCalls, requests, failed, final: api.snapshot()};
    })()""")
    assert "alternate prompt-director" in result["error"]
    assert result["next"]
    assert result["transportCalls"] == 0
    assert result["requests"] == result["failed"]["requests"] == []
    assert result["failed"]["blocked"] is True
    assert result["final"] == result["failed"]
