"""Inspect real outgoing preflight schemas with offline, nonclinical VM fixtures."""

import pytest

from test_visual_preflight import NODE, evaluate


pytestmark = pytest.mark.skipif(NODE is None, reason="Node is required for preflight tests")


@pytest.fixture(scope="module")
def outgoing():
    return evaluate(r"""(async () => {
      gate.evidence = [
        {source_key:'metadata-reference-a',page_start:11},
        {source_key:'metadata-reference-b',page_start:22},
        {source_key:'metadata-reference-a',page_start:33},
        {source_key:'metadata-reference-a',page_start:11}
      ];
      story.voLines[0].narration = 'The vase rests on its "broad" stand.\nKeep its support visible.';
      story.voLines.push({n:3, visual:'A green box rests on the wooden shelf.',
        hook:'spatial: supported box', narration:'The box rests on its shelf.', anchor:'Box on shelf'});
      story.required_concepts.push('The box rests on its shelf.');
      story.review_script = 'Recall the "stand".\nRecall the hook and shelf.';
      const prepared = await api.prepare(topic, story, gate);
      return {request:requests[0].body, story, evidence:gate.evidence,
        report:prepared.report, limits:window.MnemorizedStoryContract.limits};
    })()""")


def target_branches(schema):
    return [branch for branch in schema["properties"]["clinical_findings"]["items"]["anyOf"]
            if "n" in branch["properties"]]


def target_witnesses(schema):
    witnesses = set()
    for branch in target_branches(schema):
        props = branch["properties"]
        assert branch["additionalProperties"] is False
        assert set(branch["required"]) == {"n", "field", "quote", "issue", "source_refs"}
        if props["n"]["type"] == "null":
            n = None
        else:
            assert props["n"]["type"] == "integer"
            assert len(props["n"]["enum"]) == 1
            n = props["n"]["enum"][0]
        assert len(props["field"]["enum"]) == len(props["quote"]["enum"]) == 1
        witnesses.add((n, props["field"]["enum"][0], props["quote"]["enum"][0]))
    return witnesses


def reference_pairs(reference_schema):
    pairs = set()
    for branch in reference_schema["anyOf"]:
        assert branch["type"] == "object" and branch["additionalProperties"] is False
        assert set(branch["required"]) == {"source_key", "page_start"}
        props = branch["properties"]
        assert len(props["source_key"]["enum"]) == len(props["page_start"]["enum"]) == 1
        pairs.add((props["source_key"]["enum"][0], props["page_start"]["enum"][0]))
    assert len(pairs) == len(reference_schema["anyOf"])
    return pairs


def schema_nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from schema_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from schema_nodes(child)


def test_outgoing_schema_binds_every_actual_target_and_complete_witness(outgoing):
    schema = outgoing["request"]["tools"][0]["input_schema"]
    story = outgoing["story"]
    expected = {(line["n"], field, line[field]) for line in story["voLines"]
                for field in ("anchor", "narration")}
    expected.add((None, "review_script", story["review_script"]))
    assert target_witnesses(schema) == expected
    assert len(target_branches(schema)) == len(expected) == 7
    assert outgoing["report"]["status"] == "ready"
    assert outgoing["limits"]["openingMax"] == 60


@pytest.mark.parametrize("n,field,quote", [
    (1, "anchor", 'labeled "SIGMOID"'),
    (1, "anchor", 'labeled "PRIOR DX"'),
    (3, "anchor", 'COEIN" encodes the PALM-COEIN classification'),
])
def test_outgoing_schema_excludes_captured_cross_field_quote_pairs(outgoing, n, field, quote):
    schema = outgoing["request"]["tools"][0]["input_schema"]
    assert (n, field, quote) not in target_witnesses(schema)


def test_outgoing_schema_does_not_allow_other_target_ids_fields_or_substrings(outgoing):
    witnesses = target_witnesses(outgoing["request"]["tools"][0]["input_schema"])
    line = outgoing["story"]["voLines"][0]
    for witness in [(2, "anchor", line["anchor"]), (1, "anchor", line["narration"]),
                    (1, "visual", line["visual"]), (99, "anchor", line["anchor"]),
                    (None, "anchor", line["anchor"]), (1, "narration", 'The vase rests on its')]:
        assert witness not in witnesses


def test_all_outgoing_references_bind_only_retrieved_key_page_pairs(outgoing):
    expected = {(row["source_key"], row["page_start"]) for row in outgoing["evidence"]}
    schema = outgoing["request"]["tools"][0]["input_schema"]
    references = [node["properties"]["source_refs"]["items"] for node in schema_nodes(schema)
                  if "source_refs" in node.get("properties", {})]
    assert len(references) == 8  # Seven clinical targets and the ordinary anchor review.
    for reference in references:
        assert reference_pairs(reference) == expected
        assert ("metadata-reference-a", 22) not in reference_pairs(reference)
        assert ("metadata-reference-b", 11) not in reference_pairs(reference)
        assert ("unretrieved-reference", 11) not in reference_pairs(reference)


def test_strict_tool_uses_supported_subset_without_manufacturing_clearance(outgoing):
    request = outgoing["request"]
    assert request["tools"][0]["strict"] is True
    assert request["tool_choice"] == {"type": "tool", "name": "submit_visual_preflight_review",
                                       "disable_parallel_tool_use": True}
    schema = request["tools"][0]["input_schema"]
    assert schema["properties"]["clinical_status"]["enum"] == ["supported", "needs_repair", "source_gap"]
    for node in schema_nodes(schema):
        assert not {"oneOf", "const", "maxItems", "minLength", "maxLength"} & node.keys()
        assert node.get("minItems", 1) in (0, 1)
        assert all(not isinstance(value, (dict, list)) for value in node.get("enum", []))
    assert any(set(branch["properties"]) == {"issue"} for branch in
               schema["properties"]["clinical_findings"]["items"]["anyOf"])
    system = request["system"]
    assert "label complaints belong to visual review, not clinical_findings" in system
    assert "mnemonic count or HOOK/VISUAL relationship" in system
    assert "never manufacture supported status" in system


@pytest.mark.parametrize("source_field,quote", [
    ("visual", 'labeled "SIGMOID"'),
    ("visual", 'labeled "PRIOR DX"'),
    ("hook", 'COEIN" encodes the PALM-COEIN classification'),
])
def test_existing_invalid_reviews_still_block_without_relabeling_or_repair(source_field, quote):
    result = evaluate(r"""(async () => {
      story.voLines[0][input.field] += ' ' + input.quote;
      const value = {clinical_status:'needs_repair',clinical_findings:[{
        n:1,field:'anchor',quote:input.quote,issue:'Fixture finding quotes the wrong field.',
        source_refs:clone(gate.evidence)}],anchors:[],scene:null};
      const before = JSON.stringify({story,value});
      replies.push({result:value});
      const error = await rejected(() => api.prepare(topic,story,gate));
      return {error,report:api.getReport(),repairs:repairs.length,calls:requests.length,
        unchanged:before === JSON.stringify({story,value}),
        finding:requests[0].body.tools[0].input_schema.properties.clinical_findings.items};
    })()""", {"field": source_field, "quote": quote})
    assert "exact quote from the current target field" in result["error"]
    assert result["report"]["status"] == "blocked" and result["report"]["attempts"] == []
    assert result["repairs"] == 0 and result["calls"] == 1 and result["unchanged"]
    assert (1, "anchor", quote) not in target_witnesses({"properties": {
        "clinical_findings": {"items": result["finding"]}}})


@pytest.mark.parametrize("status", ["needs_repair", "source_gap"])
def test_real_clinical_or_source_failure_cannot_be_turned_into_supported_review(status):
    result = evaluate(r"""(async () => {
      window.MnemorizedFirstAttempt = {isActive:() => true,fail:() => {}};
      const value = input === 'source_gap'
        ? {clinical_status:input,clinical_findings:[{issue:'The requested fixture support is absent.'}],anchors:[],scene:null}
        : clinicalReview();
      replies.push({result:value});
      const error = await rejected(() => api.prepare(topic,story,gate));
      return {error,status:api.getReport().status,repairs:repairs.length,calls:requests.length,
        originalDisposition:value.clinical_status};
    })()""", status)
    assert result["error"] and result["status"] == "blocked"
    assert result["repairs"] == 0 and result["calls"] == 1
    assert result["originalDisposition"] == status


def test_current_field_witness_is_rebuilt_after_permitted_clinical_repair():
    result = evaluate(r"""(async () => {
      const oldNarration = story.voLines[0].narration;
      replies.push({result:clinicalReview()},{});
      const prepared = await api.prepare(topic,story,gate);
      return {oldNarration,newNarration:prepared.story.voLines[0].narration,
        schema:requests[1].body.tools[0].input_schema,report:prepared.report};
    })()""")
    witnesses = target_witnesses(result["schema"])
    assert (1, "narration", result["newNarration"]) in witnesses
    assert (1, "narration", result["oldNarration"]) not in witnesses
    assert result["report"]["clinical_repair_count"] == 1


def test_legacy_valid_substring_and_supported_review_validation_stay_compatible():
    result = evaluate(r"""(() => {
      const value = clinicalReview();
      value.clinical_findings[0].quote = 'vase rests on its';
      return {clinical:api.validateReview(value,story,gate.evidence),
        supported:api.validateReview(makeReview(),story,gate.evidence)};
    })()""")
    assert result["clinical"]["clinical_status"] == "needs_repair"
    assert result["clinical"]["clinical_findings"][0]["quote"] == "vase rests on its"
    assert result["supported"]["clinical_status"] == "supported"
    assert result["supported"]["clinical_findings"] == []


def test_legacy_citation_validator_still_rejects_cartesian_pair():
    result = evaluate(r"""(() => {
      const evidence = [{source_key:'first',page_start:11},{source_key:'second',page_start:22}];
      const value = clinicalReview();
      value.clinical_findings[0].source_refs = [{source_key:'first',page_start:22}];
      return errorOf(() => api.validateReview(value,story,evidence));
    })()""")
    assert "retrieved source reference" in result


@pytest.mark.parametrize("review_script", [None, ""])
def test_missing_optional_review_script_does_not_invent_quote_or_break_supported_reply(review_script):
    result = evaluate(r"""(async () => {
      story.review_script = input;
      const prepared = await api.prepare(topic,story,gate);
      return {schema:requests[0].body.tools[0].input_schema,status:prepared.report.status};
    })()""", review_script)
    assert result["status"] == "ready"
    assert all(field != "review_script" for _, field, _ in target_witnesses(result["schema"]))


def test_label_diagnostic_identifies_actual_anchor_without_clearing_risk():
    result = evaluate(r"""(() => {
      story.voLines[1].visual = 'A red kite hangs from a hook labeled "OTHER".';
      return api.inspect(story);
    })()""", pipeline=True)
    assert result["errors"] == []
    assert result["risks"] == [{"n": 2, "blocking": True,
        "message": "Image anchor 2 has text that is not an explicit short mnemonic name. Repair its VISUAL through Forge."}]


def test_inspect_uses_loaded_shared_opening_limit_and_word_counter():
    result = evaluate(r"""(() => {
      const contract = window.MnemorizedStoryContract;
      let counts = 0;
      window.MnemorizedStoryContract = {...contract,limits:{...contract.limits,openingMax:3},
        wordCount:text => {counts++;return contract.wordCount(text);}};
      story.opening = 'Bare walls surround floor.';
      return {inspection:api.inspect(story),counts};
    })()""")
    assert result["counts"] == 1
    assert result["inspection"]["errors"] == [
        "Scene opening must be a nonempty architecture description of at most 3 words."]
