"""Exercise contract retention with nonclinical fixtures, never provider calls."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest


def test_quality_contract_survives_failed_checks():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for frontend execution')
    script = r"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('frontend/scripts/forge-auth.js', 'utf8');
const start = source.indexOf('async function runMedicalQualityGate(');
const end = source.indexOf('\nfunction renderPromptData(', start);
const calls = [];
const context = vm.createContext({
  currentQualityGateData: null, currentStoryData: null,
  authState: {user: {}}, appConfig: {medicalKnowledgeEnabled: true},
  backendState: {checked: true, medicalKnowledgeConfigured: true},
  document: {getElementById: () => ({value: 'Nonclinical test topic'})},
  setStatus(){}, setStageDetail(){}, renderQualityGateMessage(){}, showBody(){},
  renderQualityGateResult(){}, getMedicalAuthToken(){return null;},
  getQualityGateConcepts(){return ['self-derived cue'];},
  MnemorizedMedicalApi: {async qualityCheck(token, body) {
    calls.push(body.required_concepts);
    if (calls.length === 1) throw new Error('offline');
    return {verdict: 'ready_for_review', evidence_status: 'matched'};
  }}
});
vm.runInContext(source.slice(start, end), context);
(async () => {
  context.story = {voLines: []};
  const failed = await vm.runInContext("runMedicalQualityGate(story, ['contract A', 'contract B'])", context);
  const success = await vm.runInContext('runMedicalQualityGate(story)', context);
  process.stdout.write(JSON.stringify({calls, failed, success, story: context.story}));
})();
"""
    result = subprocess.run(
        [node, '-e', script], cwd=Path(__file__).resolve().parents[1],
        text=True, encoding='utf-8', capture_output=True, check=True, timeout=20,
    )
    data = json.loads(result.stdout)
    assert data['failed'] is None
    assert data['calls'] == [['contract A', 'contract B']] * 2
    assert data['story']['required_concepts'] == ['contract A', 'contract B']
    assert data['success']['verdict'] == 'ready_for_review'


@pytest.mark.parametrize('mode', ['valid', 'missing', 'truncated', 'gap'])
def test_contract_review_is_independent_and_fails_closed(mode):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for frontend execution')
    script = r"""
const fs = require('fs'), vm = require('vm');
const source = fs.readFileSync('frontend/scripts/forge-auth.js', 'utf8');
const start = source.indexOf('async function reviewMedicalCoverageContract(');
const end = source.indexOf('\nasync function repairCurrentPalaceWithMedicalEvidence(', start);
const mode = process.argv[1];
let sent;
const context = vm.createContext({
  CLAUDE_MODEL: 'test', encodeHeaderValue: encodeURIComponent,
  extractXmlTag: (text, tag) => (text.match(new RegExp('<'+tag+'>([\\s\\S]*?)</'+tag+'>')) || [,''])[1],
  parseProviderContent: raw => raw.text,
  claudeFetch: async (body, stage, headers) => {
    sent = {body, stage, headers};
    return {ok: true, json: async () => ({
      stop_reason: mode === 'truncated' ? 'max_tokens' : 'end_turn',
      text: mode === 'gap' ? '<source_gap>Missing source</source_gap>' :
        '<core_concepts>Corrected A' + (mode === 'missing' ? '' : '\nCorrected B') + '</core_concepts>'
    })};
  }
});
vm.runInContext(source.slice(start, end), context);
(async () => {
  try {
    const result = await vm.runInContext("reviewMedicalCoverageContract('Sample scope', ['Old A','Old B'], 'Independent feedback')", context);
    process.stdout.write(JSON.stringify({result, sent}));
  } catch (error) { process.stdout.write(JSON.stringify({error: error.message, sent})); }
})();
"""
    result = subprocess.run(
        [node, '-e', script, mode], cwd=Path(__file__).resolve().parents[1],
        text=True, encoding='utf-8', capture_output=True, check=True, timeout=20,
    )
    data = json.loads(result.stdout)
    assert data['sent']['headers']['x-evidence-grounding'] == 'true'
    assert data['sent']['stage'] == 'medical-contract-source-review'
    assert 'generated scene' in data['sent']['body']['system']
    if mode == 'valid':
        assert data['result'] == ['Corrected A', 'Corrected B']
    else:
        assert data['error']


@pytest.mark.parametrize('mode', ['valid', 'visual', 'unsafe_visual', 'bad_target', 'bad_response'])
def test_targeted_text_repair_preserves_other_fields(mode):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for frontend execution')
    script = r"""
const fs = require('fs'), vm = require('vm');
const source = fs.readFileSync('frontend/scripts/forge-auth.js', 'utf8');
const start = source.indexOf('async function repairMedicalTextFields(');
const end = source.indexOf('\nasync function repairCurrentPalaceWithMedicalEvidence(', start);
const mode = process.argv[1];
const story = {scene_title:'Fixture', voLines:[{n:1, hook:'Old hook', narration:'Keep narration', anchor:'Keep fact', visual:'Keep visual'}], review_script:'Old review', required_concepts:['Keep scope']};
let calls = 0;
const context = vm.createContext({story,
  targets: [{anchor:1, field: mode === 'bad_target' ? 'scene_title' : mode.includes('visual') ? 'visual' : 'hook'}, {field:'review_script'}],
  CLAUDE_MODEL:'test', CLAUDE_ADVISOR_MODEL:'expert-test', encodeHeaderValue:encodeURIComponent,
  parseProviderContent:raw=>raw.text, validateStoryData:()=>({fatal:[]}),
  claudeFetch:async()=>{calls++; return {ok:true,json:async()=>({stop_reason:'end_turn',text:JSON.stringify({repairs:[
    {target:0,text:mode === 'unsafe_visual' ? 'A ruler marked 12 cm.' : 'Corrected hook'}, {target:mode === 'bad_response' ? 0 : 1,text:'Corrected review'}
  ]})})};}
});
const pipeline = fs.readFileSync('frontend/scripts/forge-pipeline.js', 'utf8');
vm.runInContext(pipeline.slice(0, pipeline.indexOf('function renderImagePromptPair(')),context);
vm.runInContext(source.slice(start,end),context);
(async()=>{try {
  const result=await vm.runInContext("repairMedicalTextFields(story,'Sample',targets,'Fix terms')",context);
  process.stdout.write(JSON.stringify({result,story,calls}));
}catch(e){process.stdout.write(JSON.stringify({error:e.message,story,calls}));}})();
"""
    result = subprocess.run(
        [node, '-e', script, mode], cwd=Path(__file__).resolve().parents[1],
        text=True, encoding='utf-8', capture_output=True, check=True, timeout=20,
    )
    data = json.loads(result.stdout)
    assert data['story']['voLines'][0]['hook'] == 'Old hook'
    assert data['story']['review_script'] == 'Old review'
    if mode in ('valid', 'visual'):
        line = data['result']['voLines'][0]
        assert line == {'n': 1, 'hook': 'Old hook' if mode == 'visual' else 'Corrected hook',
                        'narration': 'Keep narration', 'anchor': 'Keep fact',
                        'visual': 'Corrected hook' if mode == 'visual' else 'Keep visual'}
        assert data['result']['required_concepts'] == ['Keep scope']
        assert data['result']['review_script'] == 'Corrected review'
    else:
        assert data['error']
    if mode == 'bad_target':
        assert data['calls'] == 0
