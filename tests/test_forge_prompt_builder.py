"""Execute the production JS builders with nonclinical fixtures and no providers."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node is required for frontend builder execution")

RUNNER = r"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('frontend/scripts/forge-pipeline.js', 'utf8');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const boundary = source.indexOf(input.ui ? 'const demoToggle =' : 'function renderImagePromptPair(');
if (boundary < 0) throw new Error('Prompt builder boundary missing');
const context = vm.createContext({window: {}, input: input.data, console: {info() {}, warn() {}, error() {}}});
vm.runInContext(fs.readFileSync('frontend/scripts/forge-story-contract.js', 'utf8'), context);
vm.runInContext(source.slice(0, boundary), context);
if (input.ui) {
  const start = source.indexOf('function invalidateImagePrompts(');
  const end = source.indexOf("if ('serviceWorker' in navigator");
  if (start < 0 || end < start) throw new Error('Pipeline function boundary missing');
  vm.runInContext(source.slice(start, end), context);
}
Promise.resolve(vm.runInContext(input.expression, context)).then(
  result => process.stdout.write(JSON.stringify(result)),
  error => { console.error(error); process.exitCode = 1; }
);
"""


def evaluate(expression: str, data=None, *, ui=False):
    result = subprocess.run(
        [NODE, "-e", RUNNER],
        input=json.dumps({"expression": expression, "data": data, "ui": ui}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        timeout=20,
        check=True,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("topic,count", [
    ("Workshop, eight anchors", 8), ("Workshop, 9 anchors", 9),
    ("Workshop, TEN anchors", 10), ("Workshop, 8-10 anchors", None),
    ("Workshop, 18 anchors", None), ("Workshop, 8 objects", None),
])
def test_requested_anchor_count(topic, count):
    assert evaluate("requestedAnchorCount(input)", topic) == count


def test_requested_anchor_validation_preserves_shared_failures():
    result = evaluate("""(() => {
      validateStoryData = () => ({fatal:['existing failure'], warnings:['existing warning'], all:[]});
      return validateRequestedStory({voLines:[{}]}, 8);
    })()""")
    assert result["fatal"][0] == "existing failure"
    assert "Requested exactly 8 anchors; returned 1" in result["fatal"][1]
    assert result["all"] == result["fatal"] + result["warnings"]


UI_SETUP = r"""
const elements = {};
const statuses = [];
const details = [];
const alerts = [];
let providerCalls = 0;
document = {
  getElementById: id => elements[id] ||= {
    value: '', textContent: '', innerHTML: '', style: {}, disabled: false,
    classList: {add() {}, remove() {}}, removeAttribute() {}
  },
  querySelector: () => null
};
window = {...window, __mnemorizedAntigravityPrompts: ['old handoff']};
currentStoryData = null;
currentPromptData = {prompt1: 'old room', prompt2: 'old scene'};
currentQualityGateData = null;
slider = {value: '5'};
authState = {user: null};
appConfig = {demoAuthBypass: false, medicalKnowledgeEnabled: false};
backendState = {checked: true, medicalKnowledgeConfigured: false};
CLAUDE_MODEL = 'stub';
refreshAuthUI = () => {};
showBody = () => {};
setStatus = (...args) => statuses.push(args);
setStageDetail = (...args) => details.push(args);
alert = message => alerts.push(message);
isDemoMode = () => true;
isRealUserPrompt = () => false;
isOperatorMode = () => false;
demoDelay = async () => {};
escapeHtml = formatNarrationHtml = formatReviewBullets = text => text;
renderQualityGateMessage = () => {};
setCurrentPalaceData = (story, prompt1, prompt2) => {
  currentStoryData = story; currentPromptData = {prompt1, prompt2};
};
claudeFetch = async () => { providerCalls++; throw new Error('Unexpected provider call'); };
document.getElementById('topic').value = 'Ordinary objects';
for (const id of ['prompt-copy-1', 'prompt-copy-2']) document.getElementById(id).value = 'stale prompt';
for (const id of ['img-prompt-1', 'img-prompt-2']) document.getElementById(id).textContent = 'stale prompt';
const snapshot = () => ({
  copies: ['prompt-copy-1', 'prompt-copy-2'].map(id => elements[id].value),
  panels: ['img-prompt-1', 'img-prompt-2'].map(id => elements[id].textContent),
  state: currentPromptData,
  staged: window.__mnemorizedAntigravityPrompts || null,
  forgeDisabled: document.getElementById('forge-btn').disabled,
  statuses, details, alerts, providerCalls
});
"""


def anchors():
    # Distinct ordinary objects, not invented medical anchors or clinical prose.
    objects = ["vase", "kite", "basket", "drum", "chair", "ladder", "wheel", "bell", "ribbon", "lantern"]
    return [
        {
            "n": index + 1,
            "visual": (
                f"A large {obj} rests beside a plain wooden stand, with a broad clear "
                "silhouette and a brightly colored edge separated from its surroundings "
                f"by open space, ending in a distinctive {obj} finial"
            ),
            "hook": "shape",
        }
        for index, obj in enumerate(objects)
    ]


def test_full_scene_is_compact_and_preserves_every_visual():
    source = anchors()
    result = evaluate("composeImagePromptPair('A spacious workshop with a wide open floor.', assignZones(input))", source)
    prompt = result["prompt2"]
    assert 400 <= len(prompt.split()) <= 600
    assert len(prompt) <= 7800
    for anchor in source:
        assert anchor["visual"].lower() in prompt.lower()
    assert prompt.endswith("the entire illustration is text-free.")
    assert "Every surface and all empty space stay blank and unmarked" in prompt
    assert prompt.count("RENDERABLE TEXT ALLOWLIST") == 1
    assert "..." not in prompt
    assert "\n- " not in prompt


def test_long_visual_tail_survives_old_word_caps():
    visual = "A broad sculpture " + "with a curved rim " * 13 + "beside a tiny unique finial"
    result = evaluate("buildImageAnchorLines(assignZones(input))", [{"visual": visual}])
    assert visual.lower() in result.lower()
    assert result.endswith("tiny unique finial.")


@pytest.mark.parametrize("visual", [
    "Indoors at the kiln, a worker holds a ceramic bowl",
    "Outdoors beside the kiln, a worker holds a ceramic bowl",
])
def test_existing_indoor_or_outdoor_location_does_not_gain_fallback_zone(visual):
    result = evaluate("buildImageAnchorLines(input)", [{"visual": visual, "zone": "FOREGROUND LEFT"}])
    assert result == visual + "."


@pytest.mark.parametrize("visual", [
    "An alarm bell rings beside the doorway, all in the far room",
    "A giant pipe runs near the left wall",
    "A red lantern hangs in the floor center",
    "A blue cart sits in the center corridor",
    "A lamp hangs from the ceiling",
])
def test_scene_placement_at_end_of_visual_does_not_gain_fallback_zone(visual):
    result = evaluate("buildImageAnchorLines(input)", [{"visual": visual, "zone": "FOREGROUND LEFT"}])
    assert result == visual + "."
    assert "foreground" not in result.lower()


def test_anatomical_left_and_object_contact_do_not_count_as_scene_placement():
    visual = "a giant hand with a tube resting on the left arm and a band on the wrist"
    result = evaluate("buildImageAnchorLines(input)", [{"visual": visual, "zone": "FOREGROUND LEFT"}])
    assert result == "In the foreground at left, " + visual + "."


def test_oversized_source_fails_without_mutating_or_dropping_anchors():
    source = anchors()
    for anchor in source:
        anchor["visual"] += " beside a broad plain surface" * 15
    result = evaluate("""(() => {
      const before = JSON.stringify(input);
      try { composeImagePromptPair('Workshop.', assignZones(input)); return {error: ''}; }
      catch (e) { return {error: e.message, unchanged: before === JSON.stringify(input)}; }
    })()""", source)
    assert "600 words" in result["error"]
    assert "no anchors were dropped" in result["error"]
    assert result["unchanged"]


def test_source_names_have_exact_allowlist_and_precision_text_is_removed():
    source = [
        {"visual": 'A figure named "Reed" carries a long reed.', "hook": "sound-alike name"},
        {"visual": 'A ruler marked "12 cm" rests across a blue wheel.', "hook": "shape"},
    ]
    result = evaluate("composeImagePromptPair('Workshop.', assignZones(input)).prompt2", source)
    assert 'named "Reed"' in result
    assert "spelled exactly on their own objects: Reed." in result
    assert "All other surfaces and empty space stay blank" in result
    assert result.count("RENDERABLE TEXT ALLOWLIST") == 1
    assert "Clothing and device surfaces stay plain and unmarked." not in result
    assert "Every surface" not in result
    assert "12 cm" not in result
    assert "blue wheel" in result


@pytest.mark.parametrize("visual", ["", 'A sign reading "DO THIS NOW".', "A ruler marked 12 cm."])
def test_missing_visuals_ambiguous_labels_and_unquoted_values_require_repair(visual):
    result = evaluate("""(() => {
      try { composeImagePromptPair('Workshop.', assignZones(input)); return ''; }
      catch (e) { return e.message; }
    })()""", [{"visual": visual}])
    assert "Repair" in result
    assert "Forge" in result


@pytest.mark.parametrize("body", ["room " * 1700, "Only the first object.", "room " * 610])
def test_director_overflow_or_missing_visuals_recompose_complete_source(body):
    result = evaluate("""normalizeImagePromptPair({
      prompt1: 'Empty workshop.', prompt2: input.body,
      scene_description: 'A spacious workshop.', director: 'gemini'
    }, assignZones(input.anchors))""", {"body": body, "anchors": anchors()})
    assert result["director"] == "local"
    assert len(result["prompt2"].split()) <= 600
    for anchor in anchors():
        assert anchor["visual"].lower() in result["prompt2"].lower()
    assert result["prompt2"].endswith("the entire illustration is text-free.")


def test_fence_replaces_stale_content_and_is_idempotent():
    result = evaluate("""(() => {
      const first = ensureTextAllowlistFence('Scene. RENDERABLE TEXT ALLOWLIST: stale', input);
      return {first, second: ensureTextAllowlistFence(first, input)};
    })()""", [{"visual": 'A figure named "Reed" holds a reed.'}])
    assert result["first"] == result["second"]
    assert "stale" not in result["first"]
    assert result["first"].count("RENDERABLE TEXT ALLOWLIST") == 1


def test_character_guard_never_returns_a_truncated_prompt():
    result = evaluate("""(() => {
      try { clampImagePrompt('x'.repeat(7801)); return ''; }
      catch (e) { return e.message; }
    })()""")
    assert "cannot be truncated" in result
    assert evaluate("clampImagePrompt('x'.repeat(7800)).length") == 7800


def test_public_builder_api_uses_all_source_lines_after_director_overflow():
    result = evaluate("""(async () => {
      backendState = {checked: true, geminiConfigured: true};
      getReplayMode = () => 'live';
      geminiPromptDirectorFetch = async () => ({ok: true, json: async () => ({
        prompt1: 'Empty workshop.', prompt2: 'room '.repeat(1700), scene_description: 'Workshop.'
      })});
      return await buildImagePromptPair('Objects', {voLines: input}, 'initial', 'director', 'fallback');
    })()""", anchors())
    assert result["prompt1"]
    assert result["prompt2"]
    assert result["scene_description"] == "Workshop."
    assert result["director"] == "local"
    for anchor in anchors():
        assert anchor["visual"].lower() in result["prompt2"].lower()


@pytest.mark.parametrize("shape", ["knot", "loop"])
def test_figure_eight_shape_is_normalized_without_changing_source(shape):
    visual = f"A figure-8 {shape} hangs beside a wooden frame."
    result = evaluate("""(() => ({
      prompt: composeImagePromptPair('Workshop.', assignZones(input)).prompt2,
      source: input[0].visual
    }))()""", [{"visual": visual, "hook": "look-alike"}])
    assert f"figure-eight {shape}" in result["prompt"]
    assert "figure-8" not in result["prompt"]
    assert result["source"] == visual


@pytest.mark.parametrize("visual", [
    "A sign reads figure-8.",
    "A sign reads figure-8 knot.",
    "A plaque printed figure-8 loop.",
    "A figure-8 knot beside a ruler marked 12 cm.",
    "A plate printed with 8 beside a knot.",
])
def test_shape_exception_does_not_allow_printed_values(visual):
    result = evaluate("""(() => {
      try { imageAnchorVisual(input, 0); return ''; }
      catch (e) { return e.message; }
    })()""", {"visual": visual})
    assert "numeric or symbolic" in result


def test_new_run_invalidates_stale_prompts_before_planning_failure():
    result = evaluate(UI_SETUP + """
    isDemoMode = () => false;
    let atRequest;
    claudeFetch = async () => {
      providerCalls++;
      atRequest = snapshot();
      throw new Error('Planning probe failed');
    };
    (async () => { await runPipeline(); return {atRequest, final: snapshot()}; })()
    """, ui=True)
    for state in [result["atRequest"], result["final"]]:
        assert state["copies"] == ["", ""]
        assert state["panels"] == ["", ""]
        assert state["state"] == {"prompt1": "", "prompt2": ""}
        assert state["staged"] is None
    assert result["final"]["forgeDisabled"] is False
    assert result["final"]["providerCalls"] == 1


@pytest.mark.parametrize("antigravity", [False, True])
def test_generation_preflight_surfaces_error_without_provider_or_handoff(antigravity):
    result = evaluate(UI_SETUP + """
    document.getElementById('prompt-copy-2').value = 'x'.repeat(7801);
    document.getElementById('image-target-antigravity').checked = input;
    document.getElementById('generate-images-btn').disabled = true;
    (async () => {
      await generateImages();
      return {...snapshot(), error: elements['gen-img-status'].textContent,
        generateDisabled: elements['generate-images-btn'].disabled};
    })()
    """, antigravity, ui=True)
    assert "cannot be truncated" in result["error"]
    assert result["copies"][1] == "x" * 7801
    assert result["providerCalls"] == 0
    assert result["staged"] is None
    assert result["generateDisabled"] is False
    assert ["prompt", "Image prompt validation blocked", "error"] in result["statuses"]


def test_existing_demo_blocks_invalid_visuals_and_restores_controls():
    result = evaluate(UI_SETUP + """
    const before = JSON.stringify(DEMO_DATA);
    (async () => {
      await runPipeline();
      return {...snapshot(), unchanged: before === JSON.stringify(DEMO_DATA),
        retainedSource: currentStoryData.voLines === DEMO_DATA.voLines};
    })()
    """, ui=True)
    assert result["forgeDisabled"] is False
    assert result["providerCalls"] == 0
    assert result["copies"] == ["", ""]
    assert result["panels"] == ["", ""]
    assert result["staged"] is None
    assert result["unchanged"] and result["retainedSource"]
    assert ["prompt", "Demo prompt validation blocked", "error"] in result["statuses"]
    assert any("numeric or symbolic" in detail[1] for detail in result["details"])


def test_stage_three_failure_invalidates_dom_and_keeps_new_story():
    result = evaluate(UI_SETUP + """
    isDemoMode = () => false;
    const slots = Object.fromEntries(Array.from({length:8}, (_,i) => ['anchor_'+(i+1), {
      hook:'spatial: supported frame', narration:'The frame rests on a stand.',
      visual:'A wooden frame rests on a stand.', anchor:'Supported frame.', review:'Recall the stand.'}]));
    const scene = {stop_reason:'tool_use',content:[{type:'tool_use',name:'submit_memory_palace',
      input:{scene_title:'Workshop',opening:'An open workshop.',anchors:slots}}]};
    claudeFetch = async () => ({ok: true,
      json: async () => ({text: 'Ordinary objects'}),
      text: async () => JSON.stringify(scene)});
    parseProviderContent = raw => raw.text;
    extractXmlTag = () => 'Ordinary objects';
    parseStoryXml = () => ({scene_title: 'Workshop', voLines: [{visual: 'A wooden frame.'}]});
    validateStoryData = () => ({fatal: [], warnings: []});
    renderStoryData = () => {};
    runMedicalQualityGate = async () => {};
    prepareImagePromptPair = async () => {
      document.getElementById('prompt-copy-2').value = 'stale during request';
      throw new Error('Prompt probe failed');
    };
    (async () => {
      await runPipeline();
      return {...snapshot(), story: currentStoryData.scene_title};
    })()
    """, ui=True)
    assert result["copies"] == ["", ""]
    assert result["panels"] == ["", ""]
    assert result["state"] == {"prompt1": "", "prompt2": ""}
    assert result["forgeDisabled"] is False
    assert result["story"] == "Workshop"
    assert any("PROMPT ERROR" in status[1] for status in result["statuses"])


def test_repair_prompt_failure_invalidates_stale_handoff_and_dom():
    result = evaluate(UI_SETUP + """
    prepareImagePromptPair = async () => { throw new Error('Rebuild probe failed'); };
    (async () => {
      await rebuildImagePromptsForStory({scene_title: 'Workshop', voLines: [{visual: 'A wooden frame.'}]});
      return {...snapshot(), story: currentStoryData.scene_title};
    })()
    """, ui=True)
    assert result["copies"] == ["", ""]
    assert result["panels"] == ["", ""]
    assert result["staged"] is None
    assert result["story"] == "Workshop"


def test_room_composer_requests_continuous_architecture_without_partitions():
    result = evaluate("""(async () => {
      let request;
      CLAUDE_MODEL = 'stub';
      claudeFetch = async (body, stage) => {
        request = {body, stage};
        return {ok: true, json: async () => ({text: 'A continuous workshop with an open floor.'})};
      };
      parseProviderContent = raw => raw.text;
      const pair = await buildClaudeImagePromptPair('Objects', {
        scene_title: 'Workshop', opening: 'A spacious room.'
      }, assignZones(input), 'room-test');
      return {request, pair};
    })()""", anchors())
    system = result["request"]["body"]["system"]
    user = result["request"]["body"]["messages"][0]["content"]
    for prompt in (system.lower(), user.lower()):
        assert "one continuous room with an open, undivided floor" in prompt
        assert "fewer than 60 words" in prompt
        assert "no divided bays, booths, panels, grids, painted zone lines, checklist walls" in prompt
        assert "architecture only" in prompt
    assert "Do NOT invent or list anchor props" in system
    assert "Do NOT name any specific objects, furniture, or tools" in user
    assert result["request"]["stage"] == "room-test"
    for anchor in anchors():
        assert anchor["visual"].lower() in result["pair"]["prompt2"].lower()
