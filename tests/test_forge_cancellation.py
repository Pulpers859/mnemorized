"""Exercise real pipeline cancellation with provider-free, nonclinical fixtures."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize('phase', ['context', 'story', 'demo1', 'demo2', 'demo3', 'demo4'])
@pytest.mark.parametrize('new_operation', [False, True])
def test_topic_edit_releases_only_its_own_forge_button(phase, new_operation):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node required')
    script = r"""
const fs=require('fs'),vm=require('vm');
const input=JSON.parse(process.argv[1]);
const source=fs.readFileSync('frontend/scripts/forge-pipeline.js','utf8');
const start=source.indexOf('async function runPipeline()');
const end=source.indexOf("if ('serviceWorker' in navigator",start);
let entered,release;
const started=new Promise(r=>entered=r), blocked=new Promise(r=>release=r);
const elements={};
const element=id=>elements[id] ||= {value:'',textContent:'',innerHTML:'',disabled:false,
 style:{},classList:{add(){},remove(){}},removeAttribute(){}};
element('topic').value='Workshop';element('style-select').value='Marker';
const ctx=vm.createContext({console:{warn(){},error(){}},document:{getElementById:element,
 querySelector:()=>null},slider:{value:'5'},window:{MnemorizedVisualPreflight:{reset(){}}},
 forgeOperation:1,currentStoryData:null,currentQualityGateData:null,
 appConfig:{demoAuthBypass:true,medicalKnowledgeEnabled:true},authState:{},
 backendState:{medicalKnowledgeConfigured:true},CLAUDE_MODEL:'stub',VISUAL_METAPHOR_LIBRARY:'',
 isDemoMode:()=>input.phase.startsWith('demo'),isRealUserPrompt:()=>false,
 DEMO_DATA:{scene_title:'Workshop',opening:'Bare workshop',voLines:[],review_script:'Fixture'},
 formatReviewBullets:()=>'',renderQualityGateMessage(){},
 escapeHtml:value=>value,
 invalidateImagePrompts(){},refreshAuthUI(){},setStatus(){},setStageDetail(){},
 showDebug(){},showBody(){},encodeHeaderValue:encodeURIComponent,
 requestedAnchorCount:()=>2,parseProviderContent:raw=>raw.text,
 extractXmlTag:(text,tag)=>(text.match(new RegExp('<'+tag+'>([\\s\\S]*?)</'+tag+'>'))||[,''])[1],
 reviewMedicalCoverageContract:async(t,c)=>c,
});
let calls=0;
let delays=0;
ctx.demoDelay=async()=>{delays++;if(input.phase==='demo'+delays){entered();await blocked;}};
ctx.claudeFetch=async()=>{
 calls++;
 if((input.phase==='context'&&calls===1)||(input.phase==='story'&&calls===2)){
  entered();await blocked;
 }
 return {ok:true,json:async()=>({text:'<core_concepts>Vase on stand\nKite on hook</core_concepts><scene_logic>A workshop.</scene_logic>'}),
 text:async()=>JSON.stringify({text:'fixture scene'})};
};
vm.runInContext(fs.readFileSync('frontend/scripts/forge-story-contract.js','utf8'),ctx);
vm.runInContext(source.slice(start,end),ctx);
(async()=>{
 const pending=vm.runInContext('runPipeline()',ctx);
 await started;element('topic').value='Changed workshop';
 if(input.new_operation){ctx.forgeOperation++;element('forge-btn').innerHTML='New generation';}
 release();await pending;
 process.stdout.write(JSON.stringify({calls,delays,disabled:element('forge-btn').disabled,label:element('forge-btn').innerHTML}));
})();
"""
    result = subprocess.run([node, '-e', script, json.dumps({'phase': phase, 'new_operation': new_operation})],
                            cwd=Path(__file__).resolve().parents[1], capture_output=True,
                            text=True, encoding='utf-8', check=True, timeout=20)
    data = json.loads(result.stdout)
    assert data['calls'] == (0 if phase.startswith('demo') else 1 if phase == 'context' else 2)
    if phase.startswith('demo'):
        assert data['delays'] == int(phase[-1])
    assert data['disabled'] is new_operation
    assert data['label'] == ('New generation' if new_operation else '\u2726 FORGE PALACE')
