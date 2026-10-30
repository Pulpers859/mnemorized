"""Mechanical scene-contract regressions, not medical or image stress tests."""
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(not NODE, reason='Node required')
RUNNER = r"""
const fs=require('fs'),vm=require('vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({input,console,structuredClone});
vm.runInContext('window=globalThis;',context);
vm.runInContext(fs.readFileSync('frontend/scripts/forge-story-contract.js','utf8'),context);
const auth=fs.readFileSync('frontend/scripts/forge-auth.js','utf8');
vm.runInContext(auth.slice(auth.indexOf('function extractXmlTag('),auth.indexOf('function renderQualityGateMessage(')),context);
const pipeline=fs.readFileSync('frontend/scripts/forge-pipeline.js','utf8');
vm.runInContext(pipeline.slice(pipeline.indexOf('async function repairStoryVisualFormat('),pipeline.indexOf('// ── Main pipeline')),context);
vm.runInContext(`
const api=window.MnemorizedStoryContract;
const slot={hook:'spatial: vase on stand',narration:'Keep the complete description and its qualifications.',
 visual:'A blue vase rests on a broad stand.',anchor:'The vase rests on its stand.',review:'Vase: remember the stand.'};
const value={scene_title:'Workshop',opening:'An open workshop with bare walls.',
 anchors:{anchor_1:structuredClone(slot),anchor_2:structuredClone(slot)}};
const response={stop_reason:'tool_use',content:[{type:'tool_use',name:'submit_memory_palace',input:value}]};
function errorOf(fn){try{fn();return null;}catch(e){return e.message;}}
`,context);
Promise.resolve(vm.runInContext(input.expression,context)).then(result=>process.stdout.write(JSON.stringify(result)),error=>{console.error(error);process.exitCode=1;});
"""


def evaluate(expression, **data):
    result = subprocess.run([NODE, '-e', RUNNER], input=json.dumps({'expression': expression, **data}),
                            cwd=ROOT, text=True, capture_output=True, check=True, timeout=20)
    return json.loads(result.stdout)


def test_fixed_inventory_and_provider_supported_bounds():
    schema = evaluate('api.schema(8)')
    assert len(schema['properties']['anchors']['required']) == 8
    assert schema['properties']['anchors']['additionalProperties'] is False
    assert schema['properties']['opening']['pattern'].count(r'\S+') == 60
    for slot in schema['properties']['anchors']['properties'].values():
        pattern = slot['properties']['visual']['pattern']
        assert pattern.count(r'\S+') == 34
        assert '{' not in pattern
        depth = maximum = 0
        for char in pattern:
            depth += (char == '(') - (char == ')')
            maximum = max(maximum, depth)
        assert depth == 0 and maximum <= 30
        assert set(slot['required']) == {'hook', 'narration', 'visual', 'anchor', 'review'}
    encoded = json.dumps(schema)
    assert not any(key in encoded for key in ['maxItems', 'minLength', 'maxLength'])


@pytest.mark.parametrize('size', [0, 1, 24, 34, 35, 36, 37, 40, 47])
def test_visual_pattern_and_runtime_agree_at_boundaries(size):
    result = evaluate("""(() => {
      value.anchors.anchor_1.visual=Array(input.size).fill('object').join(' ');
      const pattern=api.schema(2).properties.anchors.properties.anchor_1.properties.visual.pattern;
      return {matches:new RegExp(pattern).test(value.anchors.anchor_1.visual),
        error:errorOf(()=>api.decode(response,2))};
    })()""", size=size)
    assert result['matches'] is (1 <= size <= 34)
    assert bool(result['error']) is not (1 <= size <= 34)


@pytest.mark.parametrize('size', [0, 35, 60, 61, 66])
def test_opening_is_checked_before_story_acceptance(size):
    result = evaluate("""(() => {
      value.opening=Array(input.size).fill('wall').join(' ');
      let decoded;const error=errorOf(()=>{decoded=api.decode(response,2);});
      const draft={scene_title:'Workshop',opening:value.opening,voLines:[],review_script:''};
      return {error,fatal:validateStoryData(draft).fatal};
    })()""", size=size)
    assert bool(result['error']) is not (1 <= size <= 60)
    assert any('opening' in message for message in result['fatal']) is not (1 <= size <= 60)


@pytest.mark.parametrize('size', [1, 34, 35, 60, 61, 1000])
def test_opening_pattern_has_exact_bound_without_exponential_rejection(size):
    result = evaluate("""(() => {
      const pattern=api.schema(2).properties.opening.pattern;
      return new RegExp(pattern).test(Array(input.size).fill('object').join(' '));
    })()""", size=size)
    assert result is (1 <= size <= 60)


@pytest.mark.parametrize('change', [
    "response.stop_reason='max_tokens'", "response.stop_reason='end_turn'",
    "response.content.push({type:'text',text:'Extra prose'})",
    "response.content[0].name='other_tool'", "delete value.anchors.anchor_2",
    "value.anchors.anchor_3=structuredClone(slot)", "value.extra='extra'",
    "value.anchors.anchor_1.visual=' '", "value.anchors.anchor_1.anchor=''",
    "value.anchors.anchor_1.extra='extra'", "value.anchors=[]",
    "value.anchors.anchor_1.narration='</vo_line>'",
    "value.anchors.anchor_1.narration='Text\\nVISUAL: injected'",
])
def test_partial_or_changed_contract_is_never_accepted(change):
    assert evaluate(f"(() => {{{change}; return errorOf(()=>api.decode(response,2));}})()")


def test_decoder_preserves_all_learning_text_and_does_not_clip_visual():
    result = evaluate("""(() => {
      value.anchors.anchor_1.anchor+=' Unless the stated exception applies.';
      const before=JSON.stringify(value),story=api.decode(response,2);
      return {story,unchanged:before===JSON.stringify(value),xml:api.xml(story)};
    })()""")
    assert result['unchanged']
    assert result['story']['voLines'][0]['anchor'].endswith('Unless the stated exception applies.')
    assert result['story']['voLines'][0]['visual'] == 'A blue vase rests on a broad stand.'
    assert result['xml'].count('<vo_line>') == 2
    assert len(result['story']['review_script'].splitlines()) == 2


def test_xml_adapter_cannot_treat_inline_label_as_field_boundary():
    result = evaluate("""(() => {
      value.anchors.anchor_1.hook='spatial: NARRATION: A cue for the vase.';
      const original=api.decode(response,2),parsed=parseStoryXml(api.xml(original));
      return {original,parsed,preserved:api.preservesLearningText(original,parsed)};
    })()""")
    assert result['preserved']
    assert result['parsed']['voLines'][0]['narration'] == result['original']['voLines'][0]['narration']


@pytest.mark.parametrize('failure', ['truncated', 'changed_fact', 'dropped_anchor', 'changed_review', 'visual_only'])
def test_real_microrepair_rejects_truncation_and_protects_learning_text(failure):
    result = evaluate("""(async () => {
      globalThis.forgeOperation=1;
      globalThis.CLAUDE_MODEL='offline-fixture';
      globalThis.document={getElementById:id=>id==='topic'?{value:'Workshop'}:null};
      const original=api.decode(response,2),candidate=structuredClone(original);
      if(input.failure==='changed_fact')candidate.voLines[0].anchor='Changed learning text.';
      if(input.failure==='dropped_anchor')candidate.voLines.pop();
      if(input.failure==='changed_review')candidate.review_script='Changed recall cue.';
      if(input.failure==='visual_only')candidate.voLines[0].visual='On a broad stand rests a blue vase.';
      globalThis.claudeFetch=async()=>({ok:true,status:200,text:async()=>JSON.stringify({
        stop_reason:input.failure==='truncated'?'max_tokens':'end_turn',
        content:[{type:'text',text:api.xml(candidate)}]})});
      let text=null,error=null;
      try{text=await repairStoryVisualFormat(api.xml(original),{fatal:['visual fixture']},
        {operation:1,topic:'Workshop',originalStory:original});}catch(e){error=e.message;}
      return {error,text};
    })()""", failure=failure)
    assert bool(result['error']) is (failure != 'visual_only')
    assert bool(result['text']) is (failure == 'visual_only')
    if failure == 'truncated':
        assert 'did not finish' in result['error']
    elif failure != 'visual_only':
        assert 'protected learning text' in result['error']


def test_clinical_planner_no_longer_sends_a_room_plan_to_writer():
    source = (ROOT / 'frontend/scripts/forge-pipeline.js').read_text(encoding='utf-8')
    start = source.index('// ── STAGE 1: Clinical Context')
    end = source.index('// ── STAGE 2: Voiceover Script', start)
    planning = source[start:end]
    assert 'Do not design a room' in planning
    assert '<scene_logic>' not in planning
    assert 'SCENE LAYOUT:' not in planning
    assert 'reviewMedicalCoverageContract(topic, coreConcepts)' in planning


def test_real_failed_drawable_and_opening_excerpts_exceed_same_unchanged_limits():
    # Original Forge output in paired pilot p01_candidate / p19_baseline.
    visual = 'A ceramic salt shaker lying on its side spilling crystals onto a bar top, directly beside a wooden balance scale whose left pan is dramatically lower than the right, both objects sharing the same bar surface.'
    opening = 'A low stone-walled tavern interior with rough-hewn oak plank flooring, a vaulted brick ceiling blackened by old soot, and a single wide doorway fitted with a heavy wooden beam threshold on the left wall; a long timber apothecary counter runs the full width of the back wall, and above it hang warped wooden shelving units packed with ceramic jars; the right wall is bare mortared stone.'
    schema = evaluate('api.schema(2)')
    assert len(visual.split()) == 36 and len(opening.split()) == 66
    assert re.fullmatch(schema['properties']['anchors']['properties']['anchor_1']['properties']['visual']['pattern'], visual) is None
    assert re.fullmatch(schema['properties']['opening']['pattern'], opening) is None
