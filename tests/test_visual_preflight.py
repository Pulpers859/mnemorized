"""Run the actual preflight module in Node VM, with no providers or clinical facts."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node is required for preflight tests")

RUNNER = r"""
const fs = require('fs');
const vm = require('vm');
const {webcrypto} = require('crypto');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const context = vm.createContext({crypto: webcrypto, TextEncoder, URLSearchParams, input: input.data,
  console:{info() {}, warn() {}, error() {}}});
vm.runInContext(`
window = {crypto};
const clone = value => JSON.parse(JSON.stringify(value));
const topic = 'Workshop objects';
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
const pair = {prompt1: 'An empty workshop.', prompt2: 'A vase and kite in the workshop.'};
const requests = [], repairs = [], replies = [], gateChecks = [], events = [];
let repairMutation = null;
const CLAUDE_MODEL = 'stub-model';
const encodeHeaderValue = encodeURIComponent;
const parseProviderContent = raw => raw.text;
function setStageDetail() {}
function makeReview(source = story, needsRepair = false) {
  return {clinical_status: 'supported', clinical_findings: [],
    anchors: source.voLines.map((line, index) => ({n: line.n,
      status: needsRepair && index === 0 ? 'repair' : 'ready',
      relationship_quote: line.visual, why: 'The object has an explicit support relationship.',
      source_refs: clone(gate.evidence),
      risks: needsRepair && index === 0 ? ['Separate the support silhouette.'] : []})),
    scene: {status: 'ready', issues: []}};
}
function clinicalReview(targets = [{n:1, field:'narration'}], status = 'needs_repair') {
  return {clinical_status:status, clinical_findings:targets.map(target => ({...target,
    issue:'Clarify the described support relationship.', source_refs:clone(gate.evidence)})),
    anchors:[], scene:null};
}
async function claudeFetch(body, stage, headers) {
  events.push('review');
  requests.push({body: clone(body), stage, headers: clone(headers)});
  const source = JSON.parse(body.messages[0].content).lesson;
  const reply = replies.length ? replies.shift() : {};
  if (reply.throw) throw new Error(reply.throw);
  return {ok: reply.status == null || reply.status === 200, status: reply.status || 200,
    text: async () => 'Stub provider failure',
    json: async () => ({stop_reason: reply.stop || 'end_turn',
      text: reply.text === undefined
        ? JSON.stringify(reply.result || makeReview(source, reply.repair)) : reply.text})};
}
async function repairMedicalTextFields(source, requestedTopic, targets, feedback) {
  events.push(targets.every(target => target.field === 'visual') ? 'visual-repair' : 'clinical-repair');
  repairs.push({topic: requestedTopic, targets: clone(targets), feedback});
  const next = clone(source);
  for (const target of targets) {
    const owner = target.anchor == null ? next : next.voLines[target.anchor - 1];
    owner[target.field] += target.field === 'visual' ? ' Clear spacing.' : ' Clarified.';
  }
  if (repairMutation) repairMutation(next, targets);
  return next;
}
async function runMedicalQualityGate(source, required) {
  events.push('source-recheck');
  gateChecks.push({story:clone(source), required:clone(required)});
  return clone(gate);
}
function errorOf(fn) {try {fn(); return null;} catch (error) {return error.message;}}
async function rejected(fn) {try {await fn(); return null;} catch (error) {return error.message;}}
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {resolve = yes; reject = no;});
  return {promise, resolve, reject};
}
`, context);
vm.runInContext(fs.readFileSync('frontend/scripts/forge-visual-preflight.js', 'utf8'), context);
vm.runInContext('const api = window.MnemorizedVisualPreflight;', context);
if (input.pipeline || input.integration) {
  const source = fs.readFileSync('frontend/scripts/forge-pipeline.js', 'utf8');
  const prefixEnd = source.indexOf('const DEMO_DATA =');
  const invalidateStart = source.indexOf('function invalidateImagePrompts(');
  const invalidateEnd = source.indexOf('function gateImagePrompts(', invalidateStart);
  const rebuildStart = source.indexOf('async function rebuildImagePromptsForStory(');
  const rebuildEnd = source.indexOf('async function repairStoryVisualFormat(', rebuildStart);
  const exportStart = source.indexOf('function downloadForgeBundle(');
  if (prefixEnd < 0 || invalidateStart < 0 || invalidateEnd < invalidateStart ||
      rebuildStart < 0 || rebuildEnd < rebuildStart || exportStart < 0 ||
      exportStart > rebuildStart) throw new Error('Pipeline boundaries changed');
  vm.runInContext(source.slice(0, prefixEnd), context);
  vm.runInContext(source.slice(invalidateStart, invalidateEnd), context);
  vm.runInContext(source.slice(rebuildStart, rebuildEnd), context);
  vm.runInContext(source.slice(exportStart, rebuildStart), context);
  if (input.integration) {
    const auth = fs.readFileSync('frontend/scripts/forge-auth.js', 'utf8');
    const authStart = auth.indexOf('const appConfig =');
    const authEnd = auth.indexOf('function getAuthToken(');
    const repairStart = auth.indexOf('async function repairCurrentPalaceWithMedicalEvidence(');
    const repairEnd = auth.indexOf('function renderPromptData(', repairStart);
    const imageStart = source.indexOf('function gateImagePrompts(');
    const imageEnd = source.indexOf('function downloadGenImage(', imageStart);
    if ([authStart, authEnd, repairStart, repairEnd, imageStart, imageEnd].some(n => n < 0)) {
      throw new Error('Async integration boundaries changed');
    }
    vm.runInContext('window.location = {search:""};', context);
    vm.runInContext(auth.slice(authStart, authEnd), context);
    vm.runInContext(auth.slice(repairStart, repairEnd), context);
    vm.runInContext(source.slice(imageStart, imageEnd), context);
  }
}
Promise.resolve(vm.runInContext(input.expression, context)).then(
  result => process.stdout.write(JSON.stringify(result)),
  error => {console.error(error); process.exitCode = 1;}
);
"""


def evaluate(expression, data=None, *, pipeline=False, integration=False):
    result = subprocess.run(
        [NODE, "-e", RUNNER], cwd=ROOT,
        input=json.dumps({"expression": expression, "data": data, "pipeline": pipeline,
                          "integration": integration}),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=20,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("mutation", [
    "value = null",
    "delete value.clinical_status",
    "value.clinical_findings = ['Contradicts clearance']",
    "value.anchors.pop()",
    "value.anchors.push(clone(value.anchors[0]))",
    "value.anchors.reverse()",
    "value.anchors[1].n = 1",
    "value.anchors[0].why = ' '",
    "value.anchors[0].status = 'unknown'",
    "value.anchors[0].status = 'repair'",
    "delete value.scene",
    "value.scene.status = 'repair'",
    "value.scene = {status:'repair', issues:[{anchors:[99], reason:'Collision'}]}",
    "value.scene = {status:'repair', issues:[{anchors:[1], reason:''}]}",
])
def test_malformed_or_incomplete_reviews_fail_closed(mutation):
    result = evaluate("""(() => {
      let value = makeReview();
      eval(input);
      return errorOf(() => api.validateReview(value, story, gate.evidence));
    })()""", mutation)
    assert result and "Incomplete visual preflight review" in result


@pytest.mark.parametrize("quote", ["", "A blue", "The vase sits elsewhere.",
                                      "A red kite hangs from a wall hook."])
def test_relationship_quote_must_belong_to_its_own_visual(quote):
    result = evaluate("""(() => {
      const value = makeReview(); value.anchors[0].relationship_quote = input;
      return errorOf(() => api.validateReview(value, story, gate.evidence));
    })()""", quote)
    assert "absent from its VISUAL" in result


def test_verbatim_relationship_substring_is_accepted_without_claiming_semantic_proof():
    assert evaluate("""(() => {
      const value = makeReview(); value.anchors[0].relationship_quote = 'rests on a broad stand';
      return api.validateReview(value, story, gate.evidence).anchors[0].status;
    })()""") == "ready"


@pytest.mark.parametrize("refs", [[], [{"source_key": "other", "page_start": 1}],
                                  [{"source_key": "workshop-reference", "page_start": 2}],
                                  [{"source_key": "workshop-reference"}]])
def test_missing_or_mismatched_citations_fail(refs):
    result = evaluate("""(() => {
      const value = makeReview(); value.anchors[0].source_refs = input;
      return errorOf(() => api.validateReview(value, story, gate.evidence));
    })()""", refs)
    assert result and ("source" in result)


@pytest.mark.parametrize("mutation", [
    "story.required_concepts = []",
    "gate.verdict = 'needs_repair'",
    "gate.evidence_status = 'no_relevant_source'",
    "gate.evidence = []",
    "delete gate.evidence",
    "gate.missing_from_generation = ['stand']",
    "gate.ungrounded_concepts = ['hook']",
])
def test_uncleared_source_blocks_before_provider_call(mutation):
    result = evaluate("""(async () => {
      eval(input);
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, requests: requests.length, repairs: repairs.length, report: api.getReport()};
    })()""", mutation)
    assert result["error"]
    assert result["requests"] == result["repairs"] == 0
    assert result["report"]["status"] == "blocked"


@pytest.mark.parametrize("mutation", [
    "story.voLines[1].n = 1",
    "story.voLines[0].visual = ''",
    "story.voLines[0].hook = ''",
    "story.voLines[1].visual = story.voLines[0].visual",
])
def test_structural_errors_precede_paid_review(mutation):
    result = evaluate("""(async () => {
      eval(input);
      return {error: await rejected(() => api.prepare(topic, story, gate)), calls: requests.length};
    })()""", mutation)
    assert result["error"] and result["calls"] == 0


@pytest.mark.parametrize("mutation", [
    "next.voLines[0].narration += ' Changed.'",
    "next.voLines[0].anchor += ' Changed.'",
    "next.voLines[0].hook += ' Changed.'",
    "next.required_concepts.push('New scope')",
    "next.review_script += ' Changed.'",
    "next.opening += ' Changed.'",
])
def test_repairs_cannot_change_clinical_key(mutation):
    result = evaluate("""(async () => {
      const original = JSON.stringify(story);
      repairMutation = next => eval(input);
      replies.push({repair:true});
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, unchanged: JSON.stringify(story) === original, report: api.getReport()};
    })()""", mutation)
    assert "locked clinical text or scope" in result["error"]
    assert result["unchanged"]
    assert result["report"]["status"] == "blocked"


def test_two_repairs_require_three_full_reviews_and_preserve_original():
    result = evaluate("""(async () => {
      const original = JSON.stringify(story);
      replies.push({repair:true}, {repair:true}, {});
      const prepared = await api.prepare(topic, story, gate);
      return {prepared, repairs, requests, unchanged: JSON.stringify(story) === original,
        sameClinicalKey: api.clinicalKey(story) === api.clinicalKey(prepared.story)};
    })()""")
    assert result["unchanged"] and result["sameClinicalKey"]
    assert len(result["requests"]) == 3 and len(result["repairs"]) == 2
    assert result["prepared"]["report"]["repair_count"] == 2
    assert result["prepared"]["report"]["status"] == "ready"
    for request in result["requests"]:
        assert len(json.loads(request["body"]["messages"][0]["content"])["lesson"]["voLines"]) == 2
        assert request["headers"]["x-evidence-grounding"] == "true"
        assert request["headers"]["x-visual-preflight"] == "true"
    assert all(repair["targets"] == [{"anchor": 1, "field": "visual"}] for repair in result["repairs"])


def test_repair_budget_exhaustion_blocks_without_third_repair():
    result = evaluate("""(async () => {
      replies.push({repair:true}, {repair:true}, {repair:true});
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, requests: requests.length, repairs: repairs.length, report: api.getReport()};
    })()""")
    assert "budget exhausted" in result["error"]
    assert result["requests"] == 3 and result["repairs"] == 2
    assert result["report"]["status"] == "blocked"


def test_source_gap_early_return_never_routes_to_repair():
    result = evaluate("""(async () => {
      const value = {clinical_status:'source_gap',
        clinical_findings:[{issue:'The requested relationship is unsupported.'}], anchors:[], scene:null};
      replies.push({result:value});
      return {error: await rejected(() => api.prepare(topic, story, gate)),
        repairs: repairs.length, checks:gateChecks.length, calls:requests.length};
    })()""")
    assert "source_gap" in result["error"] and result["repairs"] == 0
    assert result["checks"] == 0 and result["calls"] == 1


@pytest.mark.parametrize("reply", [{"status": 402}, {"status": 503},
                                    {"throw": "Network unavailable"},
                                    {"stop": "max_tokens"}, {"text": "not JSON"},
                                    {"text": "{}"}])
def test_provider_errors_and_truncation_revoke_existing_clearance(reply):
    result = evaluate("""(async () => {
      await api.prepare(topic, story, gate); await api.bind(topic, story, pair);
      replies.push(input);
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, report: api.getReport(), repairs: repairs.length,
        stale: errorOf(() => api.assertReady(topic, story, pair.prompt1, pair.prompt2))};
    })()""", reply)
    assert result["error"] and result["stale"]
    assert result["report"]["status"] == "blocked" and result["repairs"] == 0


@pytest.mark.parametrize("mutation", [
    "candidateTopic += ' revised'",
    "candidateStory.voLines[0].visual += ' shifted'",
    "candidateStory.voLines[0].narration += ' revised'",
    "candidateStory.required_concepts.push('New unit')",
    "candidateStory.opening += ' revised'",
    "candidatePair.prompt1 += ' revised'",
    "candidatePair.prompt2 += ' revised'",
    "api.reset()",
])
def test_binding_rejects_changed_topic_story_or_either_prompt(mutation):
    result = evaluate("""(async () => {
      await api.prepare(topic, story, gate); await api.bind(topic, story, pair);
      let candidateTopic = topic;
      const candidateStory = clone(story), candidatePair = clone(pair);
      eval(input);
      return errorOf(() => api.assertReady(candidateTopic, candidateStory,
        candidatePair.prompt1, candidatePair.prompt2));
    })()""", mutation)
    assert "missing or stale" in result


def test_review_alone_is_not_bound_and_report_reads_are_copies():
    result = evaluate("""(async () => {
      await api.prepare(topic, story, gate);
      const unbound = errorOf(() => api.assertReady(topic, story, pair.prompt1, pair.prompt2));
      const staleStory = clone(story); staleStory.voLines[0].visual += ' Changed.';
      const changed = await rejected(() => api.bind(topic, staleStory, pair));
      await api.bind(topic, story, pair);
      const report = api.getReport(); report.status = 'blocked'; report.attempts.length = 0;
      return {unbound, changed, bound: errorOf(() => api.assertReady(topic, clone(story),
        pair.prompt1, pair.prompt2)), report: api.getReport()};
    })()""")
    assert result["unbound"] and result["changed"]
    assert result["bound"] is None
    assert result["report"]["status"] == "ready"
    assert len(result["report"]["attempts"]) == 1
    assert len(result["report"]["prompt_sha256"]) == 64


@pytest.mark.parametrize("completion", ["success", "failure", "repair"])
def test_superseded_review_cannot_overwrite_newer_report_or_binding(completion):
    result = evaluate("""(async () => {
      const entered = deferred(), release = deferred();
      const normalFetch = claudeFetch;
      claudeFetch = async (...args) => {
        const payload = JSON.parse(args[0].messages[0].content);
        if (payload.learner_request !== 'Old workshop') return normalFetch(...args);
        entered.resolve(); await release.promise;
        if (input === 'failure') throw new Error('Old request failed');
        return {ok:true, json:async () => ({stop_reason:'end_turn',
          text:JSON.stringify(makeReview(payload.lesson, input === 'repair'))})};
      };
      const old = rejected(() => api.prepare('Old workshop', story, gate));
      await entered.promise;
      await api.prepare(topic, story, gate); await api.bind(topic, story, pair);
      const before = JSON.stringify(api.getReport());
      release.resolve();
      return {error:await old, unchanged:before === JSON.stringify(api.getReport()),
        ready:errorOf(() => api.assertReady(topic, story, pair.prompt1, pair.prompt2)),
        repairs:repairs.length, report:api.getReport()};
    })()""", completion)
    assert result["error"]
    assert result["unchanged"] and result["ready"] is None
    assert result["repairs"] == 0
    assert len(result["report"]["attempts"]) == 1
    assert result["report"]["input_story_sha256"] == result["report"]["story_sha256"]


@pytest.mark.parametrize("phase", ["review", "repair"])
def test_reset_during_inflight_work_cannot_resurrect_report(phase):
    result = evaluate("""(async () => {
      const entered = deferred(), release = deferred();
      if (input === 'review') {
        const normalFetch = claudeFetch;
        claudeFetch = async (...args) => {
          entered.resolve(); await release.promise; return normalFetch(...args);
        };
      } else {
        replies.push({repair:true});
        const normalRepair = repairMedicalTextFields;
        repairMedicalTextFields = async (...args) => {
          entered.resolve(); await release.promise; return normalRepair(...args);
        };
      }
      const pending = rejected(() => api.prepare(topic, story, gate));
      await entered.promise; api.reset(); release.resolve();
      return {error:await pending, report:api.getReport(), calls:requests.length,
        ready:errorOf(() => api.assertReady(topic, story, pair.prompt1, pair.prompt2))};
    })()""", phase)
    assert "superseded" in result["error"]
    assert result["report"] is None and result["ready"]
    assert result["calls"] == 1


def test_superseded_repair_cannot_publish_or_start_another_review():
    result = evaluate("""(async () => {
      const entered = deferred(), release = deferred();
      replies.push({repair:true});
      const normalRepair = repairMedicalTextFields;
      repairMedicalTextFields = async (...args) => {
        entered.resolve(); await release.promise; return normalRepair(...args);
      };
      const old = rejected(() => api.prepare('Old workshop', story, gate));
      await entered.promise;
      await api.prepare(topic, story, gate); await api.bind(topic, story, pair);
      const before = JSON.stringify(api.getReport());
      release.resolve();
      return {error:await old, unchanged:before === JSON.stringify(api.getReport()),
        calls:requests.length,
        ready:errorOf(() => api.assertReady(topic, story, pair.prompt1, pair.prompt2))};
    })()""")
    assert "superseded" in result["error"]
    assert result["unchanged"] and result["ready"] is None
    assert result["calls"] == 2


@pytest.mark.parametrize("hash_number", [1, 2])
@pytest.mark.parametrize("replacement", ["reset", "newer"])
def test_binding_cancellation_at_either_digest_cannot_restore_stale_binding(hash_number, replacement):
    result = evaluate("""(async () => {
      await api.prepare('Old workshop', story, gate);
      const entered = deferred(), release = deferred();
      const normalCrypto = window.crypto;
      let digestCalls = 0;
      window.crypto = {subtle:{digest:async (...args) => {
        if (++digestCalls === input.hashNumber) {entered.resolve(); await release.promise;}
        return normalCrypto.subtle.digest(...args);
      }}};
      const old = rejected(() => api.bind('Old workshop', story, pair));
      await entered.promise;
      if (input.replacement === 'reset') api.reset();
      else {
        await api.prepare(topic, story, gate); await api.bind(topic, story, pair);
      }
      const before = JSON.stringify(api.getReport());
      release.resolve();
      return {error:await old, unchanged:before === JSON.stringify(api.getReport()),
        report:api.getReport(),
        oldReady:errorOf(() => api.assertReady('Old workshop', story, pair.prompt1, pair.prompt2)),
        newReady:errorOf(() => api.assertReady(topic, story, pair.prompt1, pair.prompt2))};
    })()""", {"hashNumber": hash_number, "replacement": replacement})
    assert result["error"] and result["unchanged"] and result["oldReady"]
    if replacement == "reset":
        assert result["report"] is None and result["newReady"]
    else:
        assert result["report"]["status"] == "ready" and result["newReady"] is None


def test_invalidation_retains_blocked_report_and_revokes_ready_binding():
    result = evaluate("""(async () => {
      replies.push({status:503});
      await rejected(() => api.prepare(topic, story, gate));
      const blocked = JSON.stringify(api.getReport());
      api.invalidate();
      const keptBlocked = JSON.stringify(api.getReport()) === blocked;
      await api.prepare(topic, story, gate); await api.bind(topic, story, pair);
      api.invalidate();
      return {keptBlocked, report:api.getReport(),
        ready:errorOf(() => api.assertReady(topic, story, pair.prompt1, pair.prompt2))};
    })()""")
    assert result["keptBlocked"] and result["ready"]
    assert result["report"]["status"] == "stale"


@pytest.mark.parametrize("format_name, accepted", [
    ("plain", True),
    ("fenced", True),
    ("leading_commentary", False),
    ("trailing_commentary", False),
    ("fenced_commentary", False),
    ("two_fences", False),
    ("broken_fenced_json", False),
])
def test_review_json_fence_is_only_unwrapped_as_a_complete_outer_envelope(format_name, accepted):
    result = evaluate(r"""(async () => {
      const json = JSON.stringify(makeReview());
      const fenced = '```json\n' + json + '\n```';
      const formats = {
        plain: ' \n' + json + '\n ',
        fenced: ' \n' + fenced + '\n ',
        leading_commentary: 'Here is the review:\n' + json,
        trailing_commentary: json + '\nEverything looks good.',
        fenced_commentary: 'Here is the review:\n' + fenced,
        two_fences: fenced + '\n' + fenced,
        broken_fenced_json: '```json\n{"clinical_status":\n```'
      };
      replies.push({text:formats[input]});
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, report:api.getReport(), calls:requests.length, repairs:repairs.length};
    })()""", format_name)
    assert (result["error"] is None) is accepted
    assert result["report"]["status"] == ("ready" if accepted else "blocked")
    assert result["calls"] == 1
    assert result["repairs"] == 0


@pytest.mark.parametrize("old_completion", ["success", "provider_error"])
@pytest.mark.parametrize("cancel_first", [False, True])
def test_obsolete_rebuild_cannot_clear_new_story_prompts_or_preflight(old_completion, cancel_first):
    result = evaluate(r"""(async () => {
      const elements = {}, statuses = [], storyWrites = [];
      document = {getElementById: id => elements[id] ||= {
        value:'', textContent:'', style:{}, removeAttribute(name) {delete this[name];}
      }};
      document.getElementById('topic').value = topic;
      currentQualityGateData = gate;
      currentStoryData = null;
      currentPromptData = {prompt1:'', prompt2:''};
      showBody = () => {};
      isOperatorMode = () => false;
      setStatus = (...args) => statuses.push(args);
      renderStoryData = () => {};
      setCurrentPalaceData = (next, prompt1, prompt2) => {
        currentStoryData = next;
        currentPromptData = {prompt1, prompt2};
        storyWrites.push(next.scene_title);
      };
      const oldStory = clone(story), newStory = clone(story);
      oldStory.scene_title = 'Old workshop'; newStory.scene_title = 'New workshop';
      newStory.voLines[0].visual = 'A green vase rests on a broad stand.';
      const entered = deferred(), release = deferred();
      const normalFetch = claudeFetch;
      claudeFetch = async (...args) => {
        const source = JSON.parse(args[0].messages[0].content).lesson;
        if (source.scene_title === oldStory.scene_title) {
          entered.resolve(); await release.promise;
          if (input.oldCompletion === 'provider_error') throw new Error('Old provider failed');
        }
        return normalFetch(...args);
      };
      const old = rebuildImagePromptsForStory(oldStory);
      await entered.promise;
      if (input.cancelFirst) window.MnemorizedForgeOperations.cancel();
      await rebuildImagePromptsForStory(newStory);
      const snapshot = () => JSON.stringify({story:currentStoryData, prompts:currentPromptData,
        report:api.getReport(), statuses, storyWrites,
        copies:[elements['prompt-copy-1'].value, elements['prompt-copy-2'].value],
        panels:[elements['img-prompt-1'].textContent, elements['img-prompt-2'].textContent]});
      const before = snapshot(); release.resolve(); await old;
      return {unchanged:before === snapshot(), title:currentStoryData.scene_title,
        report:api.getReport(), prompt2:currentPromptData.prompt2, storyWrites,
        ready:errorOf(() => api.assertReady(topic, currentStoryData,
          currentPromptData.prompt1, currentPromptData.prompt2))};
    })()""", {"oldCompletion": old_completion, "cancelFirst": cancel_first}, pipeline=True)
    assert result["unchanged"]
    assert result["title"] == "New workshop" and result["storyWrites"] == ["New workshop"]
    assert "green vase" in result["prompt2"]
    assert result["report"]["status"] == "ready" and result["ready"] is None


@pytest.mark.parametrize("mutation", [
    "value.clinical_findings = ['Unstructured finding']",
    "value.clinical_findings = []",
    "value.clinical_findings[0].issue = ''",
    "value.clinical_findings[0].n = 99",
    "value.clinical_findings[0].n = '1'",
    "value.clinical_findings[0].field = 'visual'",
    "value.clinical_findings[0].field = 'hook'",
    "value.clinical_findings[0].field = 'review_script'",
    "value.clinical_findings[0].n = null",
    "value.clinical_findings[0] = {n:null, field:'required_concepts', issue:'New scope', source_refs:gate.evidence}",
    "value.clinical_findings[0].source_refs = []",
    "value.clinical_findings[0].source_refs[0].source_key = 'unretrieved'",
    "value.clinical_findings[0].source_refs[0].page_start = 99",
])
def test_clinical_repair_requires_valid_scoped_targets_and_source_refs(mutation):
    result = evaluate("""(async () => {
      const value = clinicalReview(); eval(input); replies.push({result:value});
      return {error:await rejected(() => api.prepare(topic, story, gate)),
        repairs:repairs.length, checks:gateChecks.length};
    })()""", mutation)
    assert result["error"]
    assert result["repairs"] == result["checks"] == 0


@pytest.mark.parametrize("targets", [
    [{"n": 1, "field": "narration"}],
    [{"n": 2, "field": "anchor"}],
    [{"n": None, "field": "review_script"}],
    [{"n": 1, "field": "narration"}, {"n": 2, "field": "anchor"},
     {"n": None, "field": "review_script"}],
])
def test_clinical_patch_changes_only_selected_fields_and_gets_full_source_rereview(targets):
    result = evaluate("""(async () => {
      const original = clone(story);
      replies.push({result:clinicalReview(input)});
      const prepared = await api.prepare(topic, story, gate);
      const expected = clone(original);
      input.forEach(target => {
        const owner = target.n == null ? expected : expected.voLines[target.n - 1];
        owner[target.field] += ' Clarified.';
      });
      return {prepared, events, requests, repairs, gateChecks,
        originalUnchanged:JSON.stringify(story) === JSON.stringify(original),
        exactlyScoped:JSON.stringify(prepared.story) === JSON.stringify(expected)};
    })()""", targets)
    assert result["originalUnchanged"] and result["exactlyScoped"]
    assert result["events"] == ["review", "clinical-repair", "source-recheck", "review"]
    report = result["prepared"]["report"]
    assert report["status"] == "ready" and report["clinical_repair_count"] == 1
    assert report["repair_count"] == 0 and len(report["clinical_attempts"]) == 1
    assert report["original_story_sha256"] != report["story_sha256"]
    assert report["input_story_sha256"] == report["story_sha256"]
    assert result["gateChecks"][0]["story"] == result["prepared"]["story"]
    assert result["gateChecks"][0]["required"] == result["prepared"]["story"]["required_concepts"]
    rereview = json.loads(result["requests"][1]["body"]["messages"][0]["content"])
    assert rereview["lesson"] == result["prepared"]["story"]
    assert result["requests"][1]["stage"] == "visual-preflight-review-clinical-recheck"


@pytest.mark.parametrize("mutation", [
    "next.voLines[0].visual += ' Changed.'",
    "next.voLines[0].hook += ' Changed.'",
    "next.voLines[0].anchor += ' Changed.'",
    "next.voLines[1].narration += ' Changed.'",
    "next.voLines[1].n = 8",
    "next.voLines.pop()",
    "next.required_concepts.push('Unrequested scope')",
    "next.review_script += ' Changed.'",
    "next.opening += ' Changed.'",
    "next.scene_title += ' Changed.'",
])
def test_clinical_patch_rejects_every_unselected_change(mutation):
    result = evaluate("""(async () => {
      const before = JSON.stringify(story);
      replies.push({result:clinicalReview()}); repairMutation = next => eval(input);
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, originalUnchanged:JSON.stringify(story) === before,
        report:api.getReport(), calls:requests.length, checks:gateChecks.length};
    })()""", mutation)
    assert "unselected field" in result["error"]
    assert result["originalUnchanged"] and result["report"]["status"] == "blocked"
    assert result["calls"] == 1 and result["checks"] == 0


def test_clinical_findings_for_same_field_are_deduplicated():
    result = evaluate("""(async () => {
      const value = clinicalReview(); value.clinical_findings.push(clone(value.clinical_findings[0]));
      replies.push({result:value}); await api.prepare(topic, story, gate);
      return repairs;
    })()""")
    assert len(result) == 1
    assert result[0]["targets"] == [{"anchor": 1, "field": "narration"}]


@pytest.mark.parametrize("second_status", ["needs_repair", "source_gap"])
def test_one_clinical_repair_bound_even_when_rereview_requests_another(second_status):
    result = evaluate("""(async () => {
      replies.push({result:clinicalReview()}, {result:clinicalReview(undefined, input)});
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, events, repairs, report:api.getReport()};
    })()""", second_status)
    assert second_status in result["error"]
    assert result["events"] == ["review", "clinical-repair", "source-recheck", "review"]
    assert len(result["repairs"]) == 1
    assert result["report"]["clinical_repair_count"] == 1
    assert result["report"]["status"] == "blocked"


def test_clinical_repair_does_not_spend_two_visual_repair_allowances():
    result = evaluate("""(async () => {
      replies.push({result:clinicalReview()}, {repair:true}, {repair:true}, {});
      const prepared = await api.prepare(topic, story, gate);
      return {report:prepared.report, events, repairs};
    })()""")
    assert result["report"]["status"] == "ready"
    assert result["report"]["clinical_repair_count"] == 1
    assert result["report"]["repair_count"] == 2
    assert result["events"] == ["review", "clinical-repair", "source-recheck", "review",
                                "visual-repair", "review", "visual-repair", "review"]


def test_new_clinical_defect_after_visual_lock_cannot_start_clinical_repair():
    result = evaluate("""(async () => {
      replies.push({repair:true}, {result:clinicalReview()});
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, repairs, report:api.getReport(), checks:gateChecks.length};
    })()""")
    assert "needs_repair" in result["error"]
    assert len(result["repairs"]) == 1
    assert result["repairs"][0]["targets"] == [{"anchor": 1, "field": "visual"}]
    assert result["checks"] == 0 and result["report"]["clinical_repair_count"] == 0


@pytest.mark.parametrize("gate_failure", ["null", "throws", "needs_repair", "missing", "ungrounded"])
def test_failed_post_clinical_source_gate_blocks_before_second_critic(gate_failure):
    result = evaluate("""(async () => {
      replies.push({result:clinicalReview()});
      const normalGate = runMedicalQualityGate;
      runMedicalQualityGate = async (...args) => {
        const next = await normalGate(...args);
        if (input === 'null') return null;
        if (input === 'throws') throw new Error('Source retrieval failed');
        if (input === 'needs_repair') next.verdict = 'needs_repair';
        if (input === 'missing') next.missing_from_generation = ['Stand'];
        if (input === 'ungrounded') next.ungrounded_concepts = ['Hook'];
        return next;
      };
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, calls:requests.length, checks:gateChecks.length, report:api.getReport()};
    })()""", gate_failure)
    assert result["error"] and result["report"]["status"] == "blocked"
    assert result["calls"] == result["checks"] == 1


def test_rereview_uses_refreshed_source_gate_citations():
    result = evaluate("""(async () => {
      const refreshed = clone(gate); refreshed.evidence[0].page_start = 2;
      runMedicalQualityGate = async () => refreshed;
      const supported = makeReview();
      supported.anchors.forEach(row => row.source_refs = clone(refreshed.evidence));
      replies.push({result:clinicalReview()}, {result:supported});
      await api.prepare(topic, story, gate);
      return {citations:JSON.parse(requests[1].body.messages[0].content).citations, report:api.getReport()};
    })()""")
    assert result["citations"] == [{"source_key": "workshop-reference", "page_start": 2}]
    assert result["report"]["status"] == "ready"


def test_clinical_patch_provider_error_is_not_retried():
    result = evaluate("""(async () => {
      replies.push({result:clinicalReview()});
      repairMutation = () => {throw new Error('Clinical patch provider failed');};
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, events, report:api.getReport()};
    })()""")
    assert "Clinical patch provider failed" in result["error"]
    assert result["events"] == ["review", "clinical-repair"]
    assert result["report"]["status"] == "blocked"


@pytest.mark.parametrize("phase", ["clinical-repair", "source-recheck"])
def test_cancelled_clinical_path_cannot_start_rereview_or_overwrite_new_clearance(phase):
    result = evaluate("""(async () => {
      const entered = deferred(), release = deferred();
      replies.push({result:clinicalReview()});
      if (input === 'clinical-repair') {
        const normalRepair = repairMedicalTextFields;
        repairMedicalTextFields = async (...args) => {
          entered.resolve(); await release.promise; return normalRepair(...args);
        };
      } else {
        const normalGate = runMedicalQualityGate;
        runMedicalQualityGate = async (...args) => {
          entered.resolve(); await release.promise; return normalGate(...args);
        };
      }
      const old = rejected(() => api.prepare('Old workshop', story, gate));
      await entered.promise;
      await api.prepare(topic, story, gate); await api.bind(topic, story, pair);
      const before = JSON.stringify(api.getReport()); release.resolve();
      return {error:await old, unchanged:before === JSON.stringify(api.getReport()), calls:requests.length,
        ready:errorOf(() => api.assertReady(topic, story, pair.prompt1, pair.prompt2))};
    })()""", phase)
    assert "superseded" in result["error"]
    assert result["unchanged"] and result["ready"] is None and result["calls"] == 2


@pytest.mark.parametrize("risk", ["Unresolved support collision", {"risk": "Unresolved support collision"}])
def test_ready_with_risk_is_downgraded_without_mutating_original(risk):
    result = evaluate("""(() => {
      const original = makeReview(); original.anchors[0].risks = [input];
      const before = JSON.stringify(original);
      const normalized = api.validateReview(original, story, gate.evidence);
      return {normalized, unchanged:JSON.stringify(original) === before};
    })()""", risk)
    row = result["normalized"]["anchors"][0]
    assert result["unchanged"]
    assert row["status"] == "repair" and row["reported_status"] == "ready"
    assert row["risks"] == ["Unresolved support collision"]


@pytest.mark.parametrize("risk", [None, {}, {"risk": " "}, {"risk": 1}, 1, ""])
def test_risk_normalization_rejects_malformed_or_empty_values(risk):
    result = evaluate("""(() => {
      const original = makeReview(); original.anchors[0].risks = [input];
      return errorOf(() => api.validateReview(original, story, gate.evidence));
    })()""", risk)
    assert "malformed risk" in result


def test_ready_scene_with_issues_is_downgraded_without_mutating_original():
    result = evaluate("""(() => {
      const original = makeReview();
      original.scene.issues = [{anchors:[1,2], reason:'Overlapping object placements.'}];
      const before = JSON.stringify(original);
      const normalized = api.validateReview(original, story, gate.evidence);
      return {normalized, unchanged:JSON.stringify(original) === before};
    })()""")
    assert result["unchanged"]
    assert result["normalized"]["scene"]["status"] == "repair"
    assert result["normalized"]["scene"]["reported_status"] == "ready"
    assert result["normalized"]["scene"]["issues"] == [
        {"anchors": [1, 2], "reason": "Overlapping object placements."}]


@pytest.mark.parametrize("scope", ["anchor", "scene"])
def test_downgraded_ready_reviews_enter_bounded_repair_and_require_clean_rereview(scope):
    result = evaluate("""(async () => {
      const value = makeReview();
      if (input === 'anchor') value.anchors[0].risks = [{risk:'Unclear support silhouette.'}];
      else value.scene.issues = [{anchors:[1,2], reason:'Overlapping placements.'}];
      replies.push({result:value});
      const prepared = await api.prepare(topic, story, gate);
      return {report:prepared.report, repairs, calls:requests.length};
    })()""", scope)
    assert result["report"]["status"] == "ready" and result["calls"] == 2
    assert result["report"]["repair_count"] == 1
    expected = [1] if scope == "anchor" else [1, 2]
    assert result["repairs"][0]["targets"] == [{"anchor": n, "field": "visual"} for n in expected]
    first = result["report"]["attempts"][0]["review"]
    assert (first["anchors"][0] if scope == "anchor" else first["scene"])["status"] == "repair"


def test_repeated_ready_with_unresolved_risks_never_clears_gate():
    result = evaluate("""(async () => {
      const value = makeReview(); value.anchors[0].risks = [{risk:'Unresolved silhouette.'}];
      replies.push({result:value}, {result:value}, {result:value});
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, report:api.getReport(), repairs:repairs.length, calls:requests.length};
    })()""")
    assert "budget exhausted" in result["error"]
    assert result["report"]["status"] == "blocked"
    assert result["repairs"] == 2 and result["calls"] == 3


@pytest.mark.parametrize("reply", [{"status": 402}, {"stop": "max_tokens"}, {"text": "not JSON"}])
def test_post_clinical_rereview_errors_do_not_retry_or_start_visual_repair(reply):
    result = evaluate("""(async () => {
      replies.push({result:clinicalReview()}, input);
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, report:api.getReport(), repairs, checks:gateChecks.length, calls:requests.length};
    })()""", reply)
    assert result["error"] and result["report"]["status"] == "blocked"
    assert len(result["repairs"]) == 1 and result["checks"] == 1 and result["calls"] == 2
    assert result["repairs"][0]["targets"] == [{"anchor": 1, "field": "narration"}]


def test_risk_downgrade_never_normalizes_away_contradictory_clinical_clearance():
    result = evaluate("""(async () => {
      const value = makeReview();
      value.clinical_findings = clinicalReview().clinical_findings;
      value.anchors[0].risks = [{risk:'Unresolved silhouette.'}];
      replies.push({result:value});
      return {error:await rejected(() => api.prepare(topic, story, gate)), repairs:repairs.length};
    })()""")
    assert "contradictory clinical clearance" in result["error"]
    assert result["repairs"] == 0


@pytest.mark.parametrize("review_still_needs_repair", [False, True])
def test_failed_then_valid_visual_patch_shares_total_request_budget(review_still_needs_repair):
    result = evaluate("""(async () => {
      const before = JSON.stringify(story);
      const validationError = 'Targeted repair failed validation: Anchor 1 visual is 36 words; maximum is 24.';
      replies.push({repair:true}, {repair:input});
      repairMutation = () => {if (repairs.length === 1) throw new Error(validationError);};
      let prepared;
      const error = await rejected(async () => {prepared = await api.prepare(topic, story, gate);});
      return {error, prepared, report:api.getReport(), repairs, events,
        validationError, unchanged:JSON.stringify(story) === before};
    })()""", review_still_needs_repair)
    report = result["report"]
    assert result["unchanged"]
    assert len(result["repairs"]) == report["visual_repair_requests"] == 2
    assert report["repair_count"] == 1 and len(report["attempts"]) == 2
    assert report["repair_failures"] == [{"request": 1, "error": result["validationError"]}]
    assert result["events"] == ["review", "visual-repair", "visual-repair", "review"]
    assert result["validationError"] in result["repairs"][1]["feedback"]
    assert "at most 18 words" in result["repairs"][1]["feedback"]
    if review_still_needs_repair:
        assert "budget exhausted" in result["error"] and report["status"] == "blocked"
    else:
        assert result["error"] is None and report["status"] == "ready"
        assert result["prepared"]["story"]["voLines"][0]["visual"].count("Clear spacing.") == 1


def test_two_invalid_visual_patches_abort_without_application_or_rereview():
    result = evaluate("""(async () => {
      replies.push({repair:true});
      repairMutation = () => {throw new Error('Targeted repair failed validation: VISUAL exceeds word cap.');};
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, report:api.getReport(), events, repairs:repairs.length};
    })()""")
    assert result["error"].startswith("Targeted repair failed validation:")
    report = result["report"]
    assert report["status"] == "blocked"
    assert result["repairs"] == report["visual_repair_requests"] == 2
    assert report["repair_count"] == 0 and len(report["attempts"]) == 1
    assert [item["request"] for item in report["repair_failures"]] == [1, 2]
    assert result["events"] == ["review", "visual-repair", "visual-repair"]


@pytest.mark.parametrize("error_message", [
    "Network unavailable",
    "Targeted repair did not return every requested field.",
    "Unexpected token in JSON",
    "Provider failed: Targeted repair failed validation: not a local validation prefix",
])
def test_visual_patch_nonvalidation_errors_have_one_request_and_no_retry(error_message):
    result = evaluate("""(async () => {
      replies.push({repair:true}); repairMutation = () => {throw new Error(input);};
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, report:api.getReport(), events, repairs:repairs.length};
    })()""", error_message)
    assert result["error"] == error_message
    report = result["report"]
    assert report["status"] == "blocked"
    assert report["visual_repair_requests"] == result["repairs"] == 1
    assert report["repair_count"] == 0 and report["repair_failures"] == []
    assert result["events"] == ["review", "visual-repair"]


def test_visual_patch_clinical_drift_is_not_a_retryable_format_failure():
    result = evaluate("""(async () => {
      replies.push({repair:true}); repairMutation = next => {next.voLines[0].narration += ' Changed.';};
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, report:api.getReport(), repairs:repairs.length};
    })()""")
    assert "locked clinical text" in result["error"]
    assert result["repairs"] == result["report"]["visual_repair_requests"] == 1
    assert result["report"]["repair_count"] == 0 and result["report"]["repair_failures"] == []


def test_clinical_patch_validation_failure_does_not_use_visual_format_retry():
    result = evaluate("""(async () => {
      replies.push({result:clinicalReview()});
      repairMutation = () => {throw new Error('Targeted repair failed validation: Invalid clinical patch.');};
      const error = await rejected(() => api.prepare(topic, story, gate));
      return {error, report:api.getReport(), events, repairs:repairs.length};
    })()""")
    assert result["error"].startswith("Targeted repair failed validation:")
    assert result["repairs"] == 1 and result["report"]["visual_repair_requests"] == 0
    assert result["report"]["repair_failures"] == []
    assert result["events"] == ["review", "clinical-repair"]


def test_terminal_visual_failure_exports_original_and_complete_repair_history():
    result = evaluate(r"""(async () => {
      const elements = {};
      let exported = null, clicked = false;
      const shownBodies = [];
      document = {
        getElementById: id => elements[id] ||= {
          value:'', textContent:'', style:{}, removeAttribute(name) {delete this[name];}
        },
        createElement: () => ({click() {clicked = true;}})
      };
      Blob = class {constructor(parts) {exported = JSON.parse(parts.join(''));}};
      URL = {createObjectURL:() => 'stub:bundle', revokeObjectURL() {}};
      document.getElementById('topic').value = topic;
      currentQualityGateData = gate;
      currentStoryData = clone(story);
      currentPromptData = {prompt1:'old room', prompt2:'old scene'};
      setStatus = renderStoryData = renderQualityGateResult = () => {};
      showBody = id => shownBodies.push(id);
      setCurrentPalaceData = (next, prompt1, prompt2) => {
        currentStoryData = next; currentPromptData = {prompt1, prompt2};
      };
      replies.push({repair:true}, {repair:true}, {repair:true});
      await rebuildImagePromptsForStory(currentStoryData);
      const blocked = api.getReport();
      downloadForgeBundle();
      return {exported, blocked, clicked, shownBodies, original:story,
        stillBlocked:errorOf(() => api.assertReady(topic, currentStoryData, '', ''))};
    })()""", pipeline=True)
    bundle = result["exported"]
    assert result["clicked"] and result["stillBlocked"]
    assert "prompt" in result["shownBodies"]
    assert bundle["story"] == result["original"]
    assert bundle["image_prompts"] == {"prompt1": "", "prompt2": ""}
    assert bundle["generated_images"] == {"image_1": None, "image_2": None, "final": None}
    assert bundle["visual_preflight"] == result["blocked"]
    report = bundle["visual_preflight"]
    assert report["status"] == "blocked" and "budget exhausted" in report["error"]
    assert report["repair_count"] == report["visual_repair_requests"] == 2
    assert len(report["attempts"]) == 3
    first, second, last = report["attempts"]
    assert first["repairs"][0]["after"] == second["repairs"][0]["before"]
    assert second["repairs"][0]["after"] == last["review"]["anchors"][0]["relationship_quote"]
    assert len({attempt["story_sha256"] for attempt in report["attempts"]}) == 3


def test_prepared_compiler_excludes_review_script_and_preserves_separate_counted_objects():
    result = evaluate(r"""(async () => {
      document = {getElementById:() => ({value:topic})};
      currentQualityGateData = gate;
      const source = clone(story);
      source.voLines[0].visual = 'Three mugs stand stacked on a counter; one inverted mug stands beside the stack.';
      source.review_script = 'Remember the vanished banner labeled MENU.';
      source.voLines[0].narration = 'NARRATION_ONLY_SENTINEL';
      const prepared = await prepareImagePromptPair(topic, source);
      return {prompt:prepared.prompt2, source, report:api.getReport()};
    })()""", pipeline=True)
    prompt = result["prompt"].lower()
    assert "three mugs stand stacked" in prompt
    assert "one inverted mug stands beside the stack" in prompt
    assert "menu" not in prompt and "vanished banner" not in prompt
    assert "narration_only_sentinel" not in prompt
    assert result["report"]["status"] == "ready"


ASYNC_UI_SETUP = r"""
const elements = {}, uiEvents = [];
document = {getElementById: id => elements[id] ||= {
  value:'', textContent:'', innerHTML:'', style:{}, disabled:false,
  removeAttribute(name) {delete this[name];}
}};
document.getElementById('topic').value = topic;
Object.assign(appConfig, {demoAuthBypass:true, medicalKnowledgeEnabled:true});
authState = {user:{id:'test-user'}, session:{access_token:'stub-token'}};
backendState = {checked:true, reachable:true, providerAuthReady:true,
  geminiConfigured:true, medicalKnowledgeConfigured:true};
currentStoryData = clone(story);
currentQualityGateData = clone(gate);
currentPromptData = clone(pair);
for (const n of [1,2]) document.getElementById('prompt-copy-' + n).value = pair['prompt' + n];
setStatus = (...args) => uiEvents.push(['status', ...args]);
setStageDetail = (...args) => uiEvents.push(['detail', ...args]);
showBody = (...args) => uiEvents.push(['show', ...args]);
renderQualityGateMessage = (...args) => uiEvents.push(['gate-message', ...args]);
renderQualityGateResult = result => uiEvents.push(['gate-result', clone(result)]);
renderStoryData = result => uiEvents.push(['story', clone(result)]);
renderPromptData = (...args) => uiEvents.push(['prompts', ...args]);
setLibraryStatus = (...args) => uiEvents.push(['library', ...args]);
setBackendBadge = (...args) => uiEvents.push(['backend', ...args]);
openAuthModal = openConnectionModal = syncConnectionModal = (...args) => uiEvents.push(['modal', ...args]);
getMedicalAuthToken = () => 'stub-token';
getQualityGateConcepts = source => source.required_concepts;
refreshBackendStatus = async () => {};
getApiUrl = path => path;
getReplayHeaders = () => ({});
getQuotaExceededMessage = () => 'Stub quota exceeded';
forgeReplayMode = 'live';
isOperatorMode = () => false;
setCurrentPalaceData = (next, prompt1, prompt2) => {
  currentStoryData = next; currentPromptData = {prompt1, prompt2};
};
window.MnemorizedGuided = {onImageReady:src => uiEvents.push(['image', src])};
function uiSnapshot() {
  return JSON.stringify({story:currentStoryData, gate:currentQualityGateData,
    prompts:currentPromptData, elements, uiEvents, report:api.getReport()});
}
function supersede() {
  window.MnemorizedForgeOperations.cancel();
  currentStoryData = {...clone(story), scene_title:'New workshop'};
  currentQualityGateData = {...clone(gate), marker:'new gate'};
  currentPromptData = {prompt1:'new room', prompt2:'new scene'};
  document.getElementById('topic').value = 'New workshop';
  for (const n of [1,2]) document.getElementById('prompt-copy-' + n).value = currentPromptData['prompt' + n];
}
"""


@pytest.mark.parametrize("completion", ["success", "error"])
@pytest.mark.parametrize("replacement", ["operation", "request", "topic"])
def test_medical_gate_discards_obsolete_response_and_error(completion, replacement):
    result = evaluate(ASYNC_UI_SETUP + r"""(async () => {
      const pending = deferred(), started = deferred();
      let calls = 0;
      MnemorizedMedicalApi = {qualityCheck:async () => {
        calls++;
        if (calls === 1) {started.resolve(); return pending.promise;}
        return {...clone(gate), marker:'new gate'};
      }};
      const old = runMedicalQualityGate(currentStoryData);
      await started.promise;
      if (input.replacement === 'operation') supersede();
      else if (input.replacement === 'request') await runMedicalQualityGate(currentStoryData);
      else document.getElementById('topic').value = 'Changed topic';
      const before = uiSnapshot();
      if (input.completion === 'error') pending.reject(new Error('Old gate failed'));
      else pending.resolve({...clone(gate), marker:'old gate'});
      await old;
      return {unchanged:uiSnapshot() === before, calls};
    })()""", {"completion": completion, "replacement": replacement}, integration=True)
    assert result["unchanged"]
    assert result["calls"] == (2 if replacement == "request" else 1)


@pytest.mark.parametrize("completion", ["success", "error"])
def test_current_medical_gate_still_publishes_result_or_error(completion):
    result = evaluate(ASYNC_UI_SETUP + r"""(async () => {
      MnemorizedMedicalApi = {qualityCheck:async () => {
        if (input === 'error') throw new Error('Current gate failed');
        return {...clone(gate), marker:'current gate'};
      }};
      await runMedicalQualityGate(currentStoryData);
      return {gate:currentQualityGateData, events:uiEvents};
    })()""", completion, integration=True)
    if completion == "success":
        assert result["gate"]["marker"] == "current gate"
        assert any(event[0] == "gate-result" for event in result["events"])
    else:
        assert result["gate"] is None
        assert any("Check failed" in event for event in result["events"])


@pytest.mark.parametrize("completion", ["success", "error"])
@pytest.mark.parametrize("boundary", ["initial_gate", "context", "contract", "provider", "json", "gate", "rebuild"])
def test_manual_repair_cancellation_preserves_newer_story_and_ui(boundary, completion):
    result = evaluate(ASYNC_UI_SETUP + r"""(async () => {
      const pending = deferred(), started = deferred(), calls = [];
      const oldStory = {...clone(story), scene_title:'Old repaired workshop'};
      async function at(name, value) {
        calls.push(name);
        if (name === input.boundary) {started.resolve(); await pending.promise;}
        return value;
      }
      MnemorizedMedicalApi = {context:() => at('context', {context:[]}),
        qualityCheck:() => at('initial_gate', clone(gate))};
      reviewMedicalCoverageContract = (t, contract) => at('contract', contract);
      claudeFetch = () => at('provider', {ok:true,
        json:() => at('json', {text:'stub', stop_reason:'end_turn'})});
      parseStoryXml = () => clone(oldStory);
      validateStoryData = validateRequestedStory = () => ({fatal:[], warnings:[]});
      if (input.boundary === 'initial_gate') currentQualityGateData = null;
      if (input.boundary !== 'initial_gate') runMedicalQualityGate = () => at('gate', clone(gate));
      rebuildImagePromptsForStory = () => at('rebuild', null);
      const old = repairCurrentPalaceWithMedicalEvidence({redesignVisuals:true});
      await started.promise;
      supersede();
      const before = uiSnapshot(), priorCalls = calls.length;
      if (input.completion === 'error') pending.reject(new Error('Old repair failed'));
      else pending.resolve();
      await old;
      return {unchanged:uiSnapshot() === before, calls, priorCalls};
    })()""", {"boundary": boundary, "completion": completion}, integration=True)
    assert result["unchanged"]
    assert len(result["calls"]) == result["priorCalls"]


@pytest.mark.parametrize("completion", ["success", "error"])
@pytest.mark.parametrize("boundary", ["backend", "auth", "fetch", "json"])
def test_image_generation_cancellation_prevents_late_publication_and_requests(boundary, completion):
    result = evaluate(ASYNC_UI_SETUP + r"""(async () => {
      const approved = await api.prepare(topic, currentStoryData, gate);
      await api.bind(topic, approved.story, pair);
      const pending = deferred(), started = deferred(), calls = [];
      async function at(name, value) {
        calls.push(name);
        if (name === input.boundary) {started.resolve(); await pending.promise;}
        return value;
      }
      backendState.checked = input.boundary !== 'backend';
      // Production refreshBackendStatus handles transport failure internally.
      refreshBackendStatus = async () => {
        try {await at('backend', null);}
        catch (_) {backendState.reachable = false;}
      };
      supabaseClient = {auth:{refreshSession:() => at('auth', {data:{session:authState.session}})}};
      fetch = () => at('fetch', {ok:true, status:200,
        json:() => at('json', {images:[{mime_type:'image/png', data:'OLD_IMAGE'}]})});
      const old = generateImages();
      await started.promise;
      supersede();
      const before = uiSnapshot(), priorCalls = calls.length;
      if (input.completion === 'error') pending.reject(new Error('Old image failed'));
      else pending.resolve();
      await old;
      return {unchanged:uiSnapshot() === before, calls, priorCalls};
    })()""", {"boundary": boundary, "completion": completion}, integration=True)
    assert result["unchanged"]
    assert len(result["calls"]) == result["priorCalls"]


@pytest.mark.parametrize("changed", ["topic", "story", "prompt1", "prompt2", "request"])
def test_image_generation_rechecks_exact_inputs_and_request_ownership(changed):
    result = evaluate(ASYNC_UI_SETUP + r"""(async () => {
      const approved = await api.prepare(topic, currentStoryData, gate);
      await api.bind(topic, approved.story, pair);
      const pending = deferred(), started = deferred();
      let calls = 0;
      const response = data => ({ok:true, status:200,
        json:async () => ({images:[{mime_type:'image/png', data}]})});
      fetch = async () => {
        calls++;
        if (calls === 1) {started.resolve(); return pending.promise;}
        return response('NEW_IMAGE');
      };
      const old = generateImages();
      await started.promise;
      if (input === 'topic') document.getElementById('topic').value = 'Changed topic';
      else if (input === 'story') currentStoryData.voLines[0].visual += ' Different placement.';
      else if (input === 'prompt1' || input === 'prompt2') {
        document.getElementById('prompt-copy-' + input.slice(-1)).value += ' Changed.';
      } else await generateImages();
      const before = uiSnapshot();
      pending.resolve(response('OLD_IMAGE'));
      await old;
      return {before:JSON.parse(before), after:JSON.parse(uiSnapshot()), calls, events:uiEvents};
    })()""", changed, integration=True)
    assert result["calls"] == (2 if changed == "request" else 1)
    if changed == "request":
        assert result["before"] == result["after"]
        assert [event for event in result["events"] if event[0] == "image"] == [
            ["image", "data:image/png;base64,NEW_IMAGE"]]
    else:
        before, after = result["before"], result["after"]
        assert after["uiEvents"][:len(before["uiEvents"])] == before["uiEvents"]
        assert [event[:3] for event in after["uiEvents"][len(before["uiEvents"]):]] == [
            ["status", "prompt", "Image request discarded"],
            ["detail", "prompt", "The lesson or prompts changed during generation. Rebuild before rendering again."],
        ]
        before["uiEvents"] = after["uiEvents"]
        before["elements"]["generate-images-btn"]["disabled"] = False
        assert after == before


@pytest.mark.parametrize("error_message", [
    "Network unavailable", "Targeted repair did not return every requested field.",
    "Targeted repair failed validation: Invalid clinical patch.",
])
def test_failed_clinical_patch_keeps_completed_review_targets_and_error(error_message):
    result = evaluate(r"""(async () => {
      const review = clinicalReview();
      replies.push({result:review});
      repairMutation = () => {throw new Error(input);};
      await rejected(() => api.prepare(topic, story, gate));
      const report = api.getReport(); api.invalidate();
      return {report, retained:api.getReport(), review};
    })()""", error_message)
    report = result["report"]
    assert report["status"] == "blocked" and report["clinical_repair_count"] == 0
    assert report["clinical_failure"] == {
        "review": result["review"], "targets": [{"anchor": 1, "field": "narration"}],
        "error": error_message,
    }
    assert report == result["retained"]


def test_successful_clinical_patch_removes_pending_failure_record():
    result = evaluate(r"""(async () => {
      replies.push({result:clinicalReview()});
      await api.prepare(topic, story, gate);
      return api.getReport();
    })()""")
    assert result["status"] == "ready" and result["clinical_repair_count"] == 1
    assert "clinical_failure" not in result


@pytest.mark.parametrize("obsolete", [False, True])
def test_rebuild_with_owned_operation_token_preserves_owner_or_ignores_obsolete(obsolete):
    result = evaluate(ASYNC_UI_SETUP + r"""(async () => {
      const operation = window.MnemorizedForgeOperations.current();
      const source = currentStoryData;
      if (input) supersede();
      const before = uiSnapshot();
      await rebuildImagePromptsForStory(source, operation);
      return {before, after:uiSnapshot(), operation,
        current:window.MnemorizedForgeOperations.current(), calls:requests.length,
        report:api.getReport(), prompts:currentPromptData};
    })()""", obsolete, integration=True)
    if obsolete:
        assert result["before"] == result["after"] and result["calls"] == 0
    else:
        assert result["operation"] == result["current"]
        assert result["report"]["status"] == "ready" and result["calls"] == 1
        assert result["prompts"]["prompt2"]


def test_current_manual_redesign_summarizes_prior_feedback_and_passes_owned_token():
    result = evaluate(ASYNC_UI_SETUP + r"""(async () => {
      replies.push({repair:true}, {repair:true}, {repair:true});
      await rejected(() => api.prepare(topic, currentStoryData, gate));
      const prior = api.getReport(), operation = window.MnemorizedForgeOperations.current();
      let feedback, rebuildToken, sourceAtRequest;
      MnemorizedMedicalApi = {context:async () => ({context:[]})};
      reviewMedicalCoverageContract = async (t, contract, reason) => {feedback = reason; return contract;};
      claudeFetch = async () => {
        sourceAtRequest = {prompts:clone(currentPromptData), report:api.getReport()};
        return {ok:true, json:async () => ({text:'stub', stop_reason:'end_turn'})};
      };
      parseStoryXml = () => ({...clone(story), scene_title:'Redesigned workshop'});
      validateStoryData = validateRequestedStory = () => ({fatal:[], warnings:[]});
      runMedicalQualityGate = async () => {currentQualityGateData = clone(gate); return currentQualityGateData;};
      rebuildImagePromptsForStory = async (source, token) => {
        rebuildToken = token;
        currentPromptData = {prompt1:'new room', prompt2:'new scene'};
      };
      await repairCurrentPalaceWithMedicalEvidence({redesignVisuals:true});
      return {prior, feedback, sourceAtRequest, operation, rebuildToken,
        current:window.MnemorizedForgeOperations.current(), story:currentStoryData,
        prompts:currentPromptData, events:uiEvents};
    })()""", integration=True)
    assert result["prior"]["status"] == "blocked"
    assert '"clinical_status":"supported"' in result["feedback"]
    assert "Previous visual encoding did not clear preflight." in result["feedback"]
    assert "Separate the support silhouette." not in result["feedback"]
    assert "relationship_quote" not in result["feedback"]
    assert result["sourceAtRequest"] == {"prompts": {"prompt1": "", "prompt2": ""}, "report": None}
    assert result["current"] == result["rebuildToken"] == result["operation"] + 1
    assert result["story"]["scene_title"] == "Redesigned workshop"
    assert result["prompts"]["prompt2"] == "new scene"
    assert any(event[0] == "library" and event[-1] == "success" for event in result["events"])


@pytest.mark.parametrize("boundary", ["unauthorized_refresh", "transient_backoff"])
def test_canceled_image_retry_does_not_send_another_request(boundary):
    result = evaluate(ASYNC_UI_SETUP + r"""(async () => {
      const approved = await api.prepare(topic, currentStoryData, gate);
      await api.bind(topic, approved.story, pair);
      const pending = deferred(), started = deferred();
      let fetches = 0, refreshes = 0;
      supabaseClient = {auth:{refreshSession:async () => {
        refreshes++;
        if (input === 'unauthorized_refresh' && refreshes === 2) {
          started.resolve(); await pending.promise;
        }
        return {data:{session:{access_token:'refreshed-stub'}}};
      }}};
      setTimeout = callback => {
        started.resolve(); pending.promise.then(callback); return 0;
      };
      fetch = async () => {
        fetches++;
        return {ok:false, status:input === 'unauthorized_refresh' ? 401 : 502};
      };
      const old = generateImages();
      await started.promise;
      supersede();
      const before = uiSnapshot();
      pending.resolve(); await old;
      return {unchanged:uiSnapshot() === before, fetches, refreshes};
    })()""", boundary, integration=True)
    assert result["unchanged"] and result["fetches"] == 1
    assert result["refreshes"] == (2 if boundary == "unauthorized_refresh" else 1)


def test_obsolete_image_backend_refresh_rejection_does_not_escape_or_write_ui():
    result = evaluate(ASYNC_UI_SETUP + r"""(async () => {
      const approved = await api.prepare(topic, currentStoryData, gate);
      await api.bind(topic, approved.story, pair);
      const pending = deferred(), started = deferred();
      let fetches = 0;
      backendState.checked = false;
      refreshBackendStatus = async () => {started.resolve(); await pending.promise;};
      fetch = async () => {fetches++; throw new Error('Unexpected image request');};
      const old = generateImages();
      await started.promise;
      supersede();
      const before = uiSnapshot();
      pending.reject(new Error('Unexpected health-helper rejection'));
      const error = await rejected(() => old);
      return {error, unchanged:uiSnapshot() === before, fetches};
    })()""", integration=True)
    assert result == {"error": None, "unchanged": True, "fetches": 0}


def test_new_flow_invalidation_reenables_generation_and_clears_old_outputs():
    result = evaluate(ASYNC_UI_SETUP + r"""(async () => {
      const approved = await api.prepare(topic, currentStoryData, gate);
      await api.bind(topic, approved.story, pair);
      document.getElementById('generate-images-btn').disabled = true;
      for (const id of ['gen-img-1-el', 'gen-img-2-el', 'gen-img-result-el']) {
        document.getElementById(id).src = 'data:image/png;base64,OLD_IMAGE';
      }
      invalidateImagePrompts();
      return {disabled:elements['generate-images-btn'].disabled,
        prompts:currentPromptData, report:api.getReport(),
        copies:[elements['prompt-copy-1'].value, elements['prompt-copy-2'].value],
        images:['gen-img-1-el', 'gen-img-2-el', 'gen-img-result-el'].map(id => elements[id].src || null)};
    })()""", integration=True)
    assert not result["disabled"]
    assert result["prompts"] == {"prompt1": "", "prompt2": ""}
    assert result["copies"] == ["", ""] and result["images"] == [None, None, None]
    assert result["report"]["status"] != "ready"
