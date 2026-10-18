"""Run the real preservation helper in a JS VM with nonclinical, offline replies."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest


SCRIPT = r"""
const fs = require('fs'), vm = require('vm');
const source = fs.readFileSync('frontend/scripts/forge-auth.js', 'utf8');
const start = source.indexOf('async function repairMedicalTextFields(');
const end = source.indexOf('\nasync function repairCurrentPalaceWithMedicalEvidence(', start);
if (start < 0 || end <= start) throw new Error('Actual repair functions not found');
const mode = process.argv[1];
const before = {
  scene_title:'Workshop', opening:'A simple workshop.',
  voLines:[
    {n:2, hook:'Contact and support', narration:'Keep this description.',
      anchor:'Wooden blocks and cone',
      visual:'Two wooden blocks rest on the floor beside a red cone.'},
    {n:7, hook:'Above and below', narration:'Keep this other description.',
      anchor:'Bell and box', visual:'A brass bell hangs above a blue box.'}
  ],
  review_script:'Keep both workshop relationships.', required_concepts:['Workshop objects']
};
const after = JSON.parse(JSON.stringify(before));
after.voLines[0].visual = 'Beside a red cone, two wooden blocks rest on the floor.';
after.voLines[1].visual = 'Above a blue box hangs a brass bell.';
let feedback = 'Shorten only the selected visuals without removing constraints.';
if (['lost','integration_lost','lost_partial'].includes(mode)) {
  after.voLines[0].visual = 'Beside a red cone, two wooden blocks rest.';
}
if (mode === 'unicode_overlap') {
  before.voLines[0].visual = 'A \u{1D400} block rests beside a caf\u00e9 sign.';
  after.voLines[0].visual = 'Beside a caf\u00e9 sign rests a \u{1D400} block.';
}
if (mode === 'authorized_change' || mode === 'bad_instruction_quote') {
  feedback = 'Move the wooden blocks from the floor to the shelf.';
  after.voLines[0].visual = 'Beside a red cone, two wooden blocks rest on the shelf.';
}
const initialBefore = JSON.stringify(before), initialAfter = JSON.stringify(after);
const targets = [{anchor:2,field:'visual'}, {anchor:7,field:'visual'}];
const constraint = (before_quote, after_quote) => ({
  before_quote, after_quote, status:'preserved', instruction_quote:'',
  reason:'The same workshop constraint is expressed in the proposed visual.'
});
// Full-clause quotes cover text, without claiming semantic inventory completeness.
const report = {targets:before.voLines.map((line,index)=>({
  target:index, constraints:[constraint(line.visual,after.voLines[index].visual)]
}))};
const support = report.targets[0].constraints[0];
if (['lost','integration_lost','lost_partial'].includes(mode)) {
  Object.assign(support, {status:'lost',after_quote:'',reason:'Floor support was omitted.'});
}
if (mode === 'lost_partial') support.before_quote = 'on the floor';
if (mode === 'unicode_overlap') {
  report.targets[0].constraints = [
    constraint('A \u{1D400} block rests',after.voLines[0].visual),
    constraint('block rests beside a caf\u00e9 sign.',after.voLines[0].visual)
  ];
}
if (mode === 'authorized_change' || mode === 'bad_instruction_quote') {
  Object.assign(support, {status:'authorized_change',
    instruction_quote:feedback,reason:'The instructions explicitly relocate the same blocks.'});
}
if (mode === 'bad_before_quote') support.before_quote = 'ON THE FLOOR';
if (mode === 'bad_after_quote') support.after_quote = 'on a floor';
if (mode === 'bad_instruction_quote') support.instruction_quote = 'Move the blocks onto a table.';
if (mode === 'partial_inventory') {
  support.before_quote = 'Two wooden blocks';
  support.after_quote = 'two wooden blocks';
}
if (mode === 'wrong_target') report.targets[0].target = 2;
if (mode === 'missing_target') report.targets.pop();
if (mode === 'duplicate_target') report.targets[1].target = 0;
const tool = {type:'tool_use',name:'submit_visual_preservation',input:report};
if (mode === 'wrong_tool') tool.name = 'submit_field_repairs';
if (mode === 'malformed_input') tool.input = null;
let content = [tool];
if (mode === 'missing_tool') content = [{type:'text',text:JSON.stringify(report)}];
if (mode === 'duplicate_tool') content = [tool,tool];
let cancelled = false, activeChecks = 0, validationCalls = 0, visualChecks = 0;
const callbacks = [], requests = [];
const options = {
  assertActive(){activeChecks++; if (cancelled) throw new Error('Operation cancelled');},
  onPreservationReview(review){callbacks.push(review);}
};
const context = vm.createContext({
  before, after, targets, feedback, options,
  expert:mode === 'authorized_change',
  CLAUDE_MODEL:'default-test', CLAUDE_ADVISOR_MODEL:'expert-test',
  encodeHeaderValue:encodeURIComponent,
  // These adjacent validators are outside this suite's preservation boundary.
  validateStoryData(){validationCalls++; return {fatal:[]};},
  imageAnchorVisual(){visualChecks++;},
  async claudeFetch(body, stage, headers){
    requests.push({body,stage,headers});
    if (body.tools[0].name === 'submit_field_repairs') {
      return {ok:true,json:async()=>{
        await Promise.resolve();
        if (mode === 'cancel_after_writer') cancelled = true;
        return {stop_reason:'tool_use',content:[{
          type:'tool_use',name:'submit_field_repairs',input:{status:'repaired',reason:'',
            repairs:after.voLines.map((line,index)=>({target:index,text:line.visual}))}
        }]};
      }};
    }
    return {ok:true,json:async()=>{
      await Promise.resolve();
      if (mode === 'cancel_late') cancelled = true;
      return {stop_reason:'tool_use',content};
    }};
  }
});
vm.runInContext(source.slice(start,end), context);
(async()=>{
  let result, error;
  try {
    result = await vm.runInContext(['integration_lost','lost_partial','cancel_after_writer'].includes(mode)
      ? "repairMedicalTextFields(before,'Workshop',targets,feedback,false,options)"
      : "reviewVisualRepairPreservation(before,after,'Workshop',targets,feedback,expert,options)", context);
  } catch (caught) {error = caught.message;}
  process.stdout.write(JSON.stringify({result,error,returned:result !== undefined,
    callbacks,requests,activeChecks,validationCalls,visualChecks,
    beforeUnchanged:JSON.stringify(before) === initialBefore,
    afterUnchanged:JSON.stringify(after) === initialAfter}));
})().catch(error=>{console.error(error);process.exitCode=1;});
"""


@pytest.mark.parametrize(
    "mode",
    [
        "preserved",
        "lost",
        "authorized_change",
        "bad_before_quote",
        "bad_after_quote",
        "bad_instruction_quote",
        "partial_inventory",
        "lost_partial",
        "unicode_overlap",
        "wrong_target",
        "missing_target",
        "duplicate_target",
        "wrong_tool",
        "missing_tool",
        "duplicate_tool",
        "malformed_input",
        "cancel_late",
        "cancel_after_writer",
        "integration_lost",
    ],
)
def test_visual_patch_preservation_boundary(mode):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for actual frontend execution")
    completed = subprocess.run(
        [node, "-e", SCRIPT, mode],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
        timeout=20,
    )
    data = json.loads(completed.stdout)
    assert data["beforeUnchanged"]
    assert data["afterUnchanged"]
    assert len(data["requests"]) == (
        2 if mode in ("integration_lost", "lost_partial") else 1
    )
    if mode == "cancel_after_writer":
        assert data["requests"][0]["stage"] == "medical-targeted-text-repair"
        assert data["error"] == "Operation cancelled"
        assert not data["returned"]
        assert data["callbacks"] == []
        assert data["validationCalls"] == 0
        assert data["visualChecks"] == 0
        assert data["activeChecks"] >= 2
        return
    request = data["requests"][-1]
    body = request["body"]
    assert request["stage"] == "visual-patch-preservation-review"
    assert request["headers"] == {
        "x-evidence-grounding": "true",
        "x-evidence-topic": "Workshop",
        "x-visual-preflight": "true",
    }
    assert body["model"] == (
        "expert-test" if mode == "authorized_change" else "default-test"
    )
    assert body["tool_choice"] == {
        "type": "tool",
        "name": "submit_visual_preservation",
        "disable_parallel_tool_use": True,
    }
    assert body["tools"][0]["strict"] is True
    payload = json.loads(body["messages"][0]["content"])
    assert [(pair["target"], pair["anchor"]) for pair in payload["pairs"]] == [
        (0, 2),
        (1, 7),
    ]
    for pair, original, proposed in zip(
        payload["pairs"],
        payload["original_lesson"]["voLines"],
        payload["proposed_lesson"]["voLines"],
    ):
        assert pair["before"] == original["visual"]
        assert pair["after"] == proposed["visual"]

    if mode in ("preserved", "authorized_change", "unicode_overlap"):
        assert data.get("error") is None
        assert data["returned"]
        assert len(data["callbacks"]) == 1
        assert data["callbacks"][0]["review"] == data["result"]
        assert data["callbacks"][0]["evidence_coverage_complete"] is True
        for pair, row in zip(payload["pairs"], data["result"]["targets"]):
            if mode == "unicode_overlap" and row["target"] == 0:
                quotes = [item["before_quote"] for item in row["constraints"]]
                assert len(quotes) == 2
                assert all(quote != pair["before"] for quote in quotes)
                first_end = len(quotes[0])
                second_start = pair["before"].index(quotes[1])
                assert 0 < second_start < first_end
                assert second_start + len(quotes[1]) == len(pair["before"])
                assert "\U0001d400" in quotes[0] and "\u00e9" in quotes[1]
            else:
                assert row["constraints"][0]["before_quote"] == pair["before"]
        support = data["result"]["targets"][0]["constraints"][0]
        assert support["status"] == (
            "authorized_change" if mode == "authorized_change" else "preserved"
        )
        assert support["instruction_quote"] == (
            payload["repair_instructions"] if mode == "authorized_change" else ""
        )
    elif mode in ("lost", "integration_lost", "lost_partial"):
        assert not data["returned"]
        assert "blocked the patch" in data["error"]
        assert len(data["callbacks"]) == 1
        assert data["callbacks"][0]["evidence_coverage_complete"] is (
            mode != "lost_partial"
        )
        assert data["callbacks"][0]["review"]["targets"][0]["constraints"][0][
            "status"
        ] == "lost"
        if mode in ("integration_lost", "lost_partial"):
            assert data["validationCalls"] == 1
            assert data["visualChecks"] == 2
            assert data["requests"][0]["stage"] == "medical-targeted-text-repair"
    elif mode == "cancel_late":
        assert data["error"] == "Operation cancelled"
        assert not data["returned"]
        assert data["callbacks"] == []
        assert data["activeChecks"] >= 2
    else:
        assert "invalid or incomplete evidence" in data["error"]
        assert not data["returned"]
        assert data["callbacks"] == []
