"""Sparse-contract integrity, not cue quality, source completeness or recall."""
import json
from pathlib import Path

import pytest

from tools.chapter_cue_sparse import build, digest, integrate_reviewed, materialize_inventory, prepare, read, write


@pytest.fixture
def packet(tmp_path):
    p = tmp_path/"packet"
    write(p/"manifest.json", {"source": {"file": "test.pdf", "sha256": "a"*64, "printed_page_offset": 100},
        "chapters": {"2": {"title": "Example", "regions": {"1": [[0, 30, 300, 800]]}}},
        "prior_before": "2", "review_date": "2026-10-24"})
    write(p/"source/gi-1.json", {"annotations": [], "spans": [
        {"text": "Head", "bbox": [20, 40, 40, 50], "font": "Bold", "size": 10, "flags": 16},
        {"text": "neighbor chapter", "bbox": [310, 40, 400, 50], "font": "Bold", "size": 10, "flags": 16}]})
    write(p/"author/inventory2.json", {"chapter_id": "2", "terms": [
        {"term": "Head", "kind": "heading", "hits": [{"at": [[1, 0]], "emphasis": "bold heading"}]}],
        "excluded_non_terms": []})
    write(tmp_path/"docs/chapter-1-cue-audit.json", {"chapter_id": "1", "entries": [
        {"term": "Head", "decision": "retain_candidate", "cue": "A literal head model.", "cue_scope": "Head only."},
        {"term": "Held", "decision": "hold", "cue": None, "cue_scope": "No selected bridge."}]})
    prepare(p, "2", tmp_path)
    write(p/"author/decisions2.json", {"chapter_id": "2", "inventory_sha256": digest(p/"author/inventory2.json"),
        "reuse": [["Head", "docs/chapter-1-cue-audit.json#Head"]], "changes": []})
    return tmp_path, p


def choices(p, change):
    path = p/"author/decisions2.json"
    data = read(path)
    change(data)
    write(path, data)


def explicit():
    return {"term": "Head", "decision": "retain_candidate", "cue": "A new named host.",
            "cue_scope": "Explicit actual head only.", "reason": "Actual named sound relation.",
            "association_status": "new_association", "association_comparison": "Different named bridge from the prior model."}


def test_source_metadata_is_copied_from_selected_spans(packet):
    root, p = packet
    result = materialize_inventory(p, "2", root)
    loc = result["terms"][0]["source_locations"][0]
    assert loc["text"] == "Head" and loc["font"] == "Bold" and loc["bbox"] == [20, 40, 40, 50]
    assert result["keyword_screen"]["items"][0]["page"] == 101


def test_highlight_count_does_not_count_other_native_annotation_types(packet):
    root, p = packet
    path = p/"source/gi-1.json"
    data = read(path)
    data["annotations"] = [[0, "Text"], [8, "Highlight"]]
    write(path, data)
    result = materialize_inventory(p, "2", root)
    assert result["keyword_screen"]["highlight_annotation_check"]["highlight_annotations_found"] == 1


def test_explicit_unchanged_reuse_inherits_only_reviewed_cue_and_scope(packet):
    root, p = packet
    bank = build(p, "2", root)
    e = bank["entries"][0]
    assert e["cue"] == "A literal head model." and e["cue_scope"] == "Head only."
    assert e["association_status"] == "unchanged_repeat" and e["change_origin"] == "existing_candidate_recount"
    assert bank["counts"] == {"selected_terms": 1, "new_candidates": 0, "reused_candidates": 1, "holds": 0}
    assert bank["production_admitted"] is False and not any(bank["evidence"].values())
    assert bank["review_status"].endswith("pending")
    assert e["source_refs"] == [[1, 0]]
    assert "source_locations" not in e  # Full source text stays in the ignored packet.


def alias_choice():
    return {"term": "Head", "prior": "docs/chapter-1-cue-audit.json#Head",
            "reason": "Only the explicit head category; other target modifiers omitted.",
            "association_comparison": "Author selected the unchanged prior bridge and depiction."}


def test_alias_adoption_copies_frozen_content_and_keeps_authored_scope_notes(packet):
    root, p = packet
    inventory = read(p/"author/inventory2.json")
    inventory["terms"][0]["term"] = "Head category alias"
    write(p/"author/inventory2.json", inventory)
    (p/"author/decisions2.json").unlink()
    prepare(p, "2", root)
    row = {**alias_choice(), "term": "Head category alias"}
    write(p/"author/decisions2.json", {"chapter_id": "2", "inventory_sha256": digest(p/"author/inventory2.json"),
                                    "reuse": [], "aliases": [row], "changes": []})
    bank = build(p, "2", root)
    e = bank["entries"][0]
    assert e["cue"] == "A literal head model." and e["cue_scope"] == "Head only."
    assert e["reason"] == row["reason"] and e["association_comparison"] == row["association_comparison"]
    assert e["association_status"] == "unchanged_repeat" and e["change_origin"] == "existing_candidate_recount"
    assert bank["sparse_provenance"]["explicit_alias_adoption_rows"] == 1
    assert bank["counts"]["reused_candidates"] == 1


@pytest.mark.parametrize("update", [{"cue": "Override"}, {"cue_scope": "Override"},
                                  {"association_status": "new_association"}, {"reason": ""},
                                  {"association_comparison": ""}, {"prior": "local:2#Head"},
                                  {"prior": "docs/chapter-1-cue-audit.json#Held"},
                                  {"prior": "../outside.json#Head"}])
def test_alias_rejects_overrides_unselected_and_unexplained_adoptions(packet, update):
    root, p = packet
    choices(p, lambda d: d.update(reuse=[], aliases=[{**alias_choice(), **update}]))
    with pytest.raises(ValueError):
        build(p, "2", root)


def test_alias_cannot_duplicate_reuse_or_bypass_frozen_prior(packet):
    root, p = packet
    choices(p, lambda d: d.update(aliases=[alias_choice()]))
    with pytest.raises(ValueError, match="Duplicate"):
        build(p, "2", root)
    choices(p, lambda d: d.update(reuse=[]))
    prior = root/"docs/chapter-1-cue-audit.json"
    original = read(prior)
    original["entries"][0]["cue"] = "Changed content."
    write(prior, original)
    with pytest.raises(ValueError, match="Changed/invalid prior"):
        build(p, "2", root)


@pytest.mark.parametrize("value", [{}, "", None, False, 0])
def test_alias_collection_must_be_an_array(packet, value):
    root, p = packet
    choices(p, lambda d: d.update(aliases=value))
    with pytest.raises(ValueError, match="must be an array"):
        build(p, "2", root)


@pytest.mark.parametrize("scope", [None, "", " "])
def test_alias_requires_real_existing_scope(packet, scope):
    root, p = packet
    prior = root/"docs/chapter-1-cue-audit.json"
    data = read(prior)
    data["entries"][0]["cue_scope"] = scope
    write(prior, data)
    freeze = read(p/"prior-freeze.json")
    freeze["docs/chapter-1-cue-audit.json"] = digest(prior)
    write(p/"prior-freeze.json", freeze)
    choices(p, lambda d: d.update(reuse=[], aliases=[alias_choice()]))
    with pytest.raises(ValueError, match="lacks inheritable"):
        build(p, "2", root)


@pytest.mark.parametrize("update", [{}, {"prior": "docs/chapter-1-cue-audit.json#Held"},
                                  {"cue": "Override"}, {"reason": ""}])
def test_cross_chapter_alias_target_uses_the_same_validation(packet, update):
    root, p = packet
    manifest = read(p/"manifest.json")
    manifest["chapters"]["3"] = manifest["chapters"]["2"]
    write(p/"manifest.json", manifest)
    write(p/"materialized/inventory2.json", materialize_inventory(p, "2", root))
    write(p/"author/decisions3.json", {"reuse": [], "aliases": [{**alias_choice(), "term": "Root", **update}], "changes": []})
    choices(p, lambda d: d.update(reuse=[], changes=[{**explicit(), "prior": "local:3#Root"}]))
    if update:
        with pytest.raises(ValueError):
            build(p, "2", root)
    else:
        assert build(p, "2", root)["entries"][0]["prior"] == "local:3#Root"


@pytest.mark.parametrize("value", [{}, "", None, False, 0])
def test_cross_chapter_alias_collection_must_be_an_array(packet, value):
    root, p = packet
    manifest = read(p/"manifest.json")
    manifest["chapters"]["3"] = manifest["chapters"]["2"]
    write(p/"manifest.json", manifest)
    write(p/"materialized/inventory2.json", materialize_inventory(p, "2", root))
    write(p/"author/decisions3.json", {"reuse": [], "aliases": value, "changes": []})
    choices(p, lambda d: d.update(reuse=[], changes=[{**explicit(), "prior": "local:3#Root"}]))
    with pytest.raises(ValueError, match="must be an array"):
        build(p, "2", root)


@pytest.mark.parametrize("field,value", [("at", [[1, 1]]), ("at", [[1, -1]]), ("at", [[1, True]])])
def test_invalid_or_foreign_source_pointers_rejected(packet, field, value):
    root, p = packet
    path = p/"author/inventory2.json"
    data = read(path)
    data["terms"][0]["hits"][0][field] = value
    write(path, data)
    with pytest.raises(ValueError):
        materialize_inventory(p, "2", root)


def test_duplicate_inventory_and_manual_metadata_rejected(packet):
    root, p = packet
    path = p/"author/inventory2.json"
    data = read(path)
    data["terms"][0]["bbox"] = [0, 0, 1, 1]
    write(path, data)
    with pytest.raises(ValueError, match="metadata belongs"):
        materialize_inventory(p, "2", root)
    data["terms"][0].pop("bbox")
    data["terms"].append({**data["terms"][0], "term": "head"})
    write(path, data)
    with pytest.raises(ValueError, match="Duplicate"):
        materialize_inventory(p, "2", root)


@pytest.mark.parametrize("rows", [[], [["Head", "docs/chapter-1-cue-audit.json#Held"]],
                                  [["Changed name", "docs/chapter-1-cue-audit.json#Head"]],
                                  [["Head", "../outside.json#Head"]],
                                  [["Head", "docs/chapter-1-cue-audit.json#Head"]]*2])
def test_missing_held_changed_name_escape_and_duplicate_reuse_rejected(packet, rows):
    root, p = packet
    choices(p, lambda d: d.update(reuse=rows))
    with pytest.raises(ValueError):
        build(p, "2", root)


def test_source_or_prior_changes_after_freeze_rejected(packet):
    root, p = packet
    path = p/"source/gi-1.json"
    original = path.read_bytes()
    data = read(path)
    data["spans"][0]["text"] = "Changed evidence"
    write(path, data)
    with pytest.raises(ValueError, match="evidence changed"):
        build(p, "2", root)
    path.write_bytes(original)
    prior = root/"docs/chapter-1-cue-audit.json"
    data = read(prior)
    data["entries"][0]["cue"] = "Changed after lookup"
    write(prior, data)
    with pytest.raises(ValueError, match="Changed/invalid prior"):
        build(p, "2", root)


@pytest.mark.parametrize("update", [{"pdf_page": 99}, {"association_status": "hold"},
                                    {"decision": "reuse_candidate"}, {"association_status": "unchanged_repeat", "change_origin": "new_proposal"}])
def test_semantic_source_override_and_accounting_contradictions_rejected(packet, update):
    root, p = packet
    item = {**explicit(), **update}
    choices(p, lambda d: d.update(reuse=[], changes=[item]))
    with pytest.raises(ValueError):
        build(p, "2", root)


def test_explicit_semantic_change_is_preserved_not_overwritten(packet):
    root, p = packet
    choices(p, lambda d: d.update(reuse=[], changes=[explicit()]))
    bank = build(p, "2", root)
    assert bank["entries"][0]["cue"] == "A new named host."
    assert bank["entries"][0]["cue_scope"] == "Explicit actual head only."


def test_duplicate_json_keys_and_packet_escape_rejected(packet):
    root, p = packet
    path = p/"duplicate.json"
    path.write_text('{"same":1,"same":2}')
    with pytest.raises(ValueError, match="Duplicate JSON"):
        read(path)
    with pytest.raises(ValueError, match="inside root"):
        materialize_inventory(root.parent/"outside", "2", root)


def test_inventory_cannot_be_silently_prepared_over_decisions(packet):
    root, p = packet
    with pytest.raises(ValueError, match="Preserve decisions"):
        prepare(p, "2", root)


@pytest.mark.parametrize("decision", ["rejected", None])
def test_prior_requires_positive_selection_even_with_a_forged_freeze(packet, decision):
    root, p = packet
    path = root/"docs/chapter-1-cue-audit.json"
    data = read(path)
    data["entries"][0]["decision"] = decision
    write(path, data)
    write(p/"prior-freeze.json", {"docs/chapter-1-cue-audit.json": digest(path)})
    with pytest.raises(ValueError, match="unselected"):
        build(p, "2", root)


@pytest.mark.parametrize("field,value", [("cue", "A different depiction."), ("cue_scope", "Different encoded scope.")])
@pytest.mark.parametrize("decision", ["retain_candidate", "reuse_candidate"])
def test_explicit_changed_copy_cannot_claim_unchanged_selected_prior(packet, field, value, decision):
    root, p = packet
    item = {**explicit(), "decision": decision, "prior": "docs/chapter-1-cue-audit.json#Head",
            "cue": "A literal head model.", "cue_scope": "Head only.", "association_status": "unchanged_repeat",
            "change_origin": "existing_candidate_recount", field: value}
    choices(p, lambda d: d.update(reuse=[], changes=[item]))
    with pytest.raises(ValueError, match="preserve cue/scope"):
        build(p, "2", root)


def approve(root, p):
    bank = build(p, "2", root)
    target = p/"materialized/chapter-2-cue-audit.json"
    write(target, bank)
    write(root/"docs/tintinalli-chapter-cue-ledger.json", {"next_chapter": {"chapter_id": "2"}, "subsequent_chapter_reviews": []})
    (root/"docs/tintinalli-chapter-cues.md").write_text("# Index\n")
    (root/"docs/review.md").write_text("# Independent review\n")
    write(p/"main-approval.json", {"chapters": {"2": digest(target)}, "source_and_conceptual_review": True,
        "scope": "Explicit independent main review.", "date": "2026-10-24", "report": "docs/review.md",
        "next_chapter": {"chapter_id": "3", "title": "Next", "status": "not_started_for_cue_review"}})
    return target


def test_main_integration_keeps_untested_state_and_refuses_overwrite(packet):
    root, p = packet
    approve(root, p)
    integrate_reviewed(p, root)
    bank = read(root/"docs/chapter-2-cue-audit.json")
    assert bank["main_integration_review"]["source_and_conceptual_review"] is True
    assert bank["production_admitted"] is False and bank["entries"][0]["tested"] is False
    assert read(root/"docs/tintinalli-chapter-cue-ledger.json")["next_chapter"]["chapter_id"] == "3"
    with pytest.raises(ValueError):
        integrate_reviewed(p, root)


def test_integration_preflight_does_not_write_partial_docs_on_stale_review(packet):
    root, p = packet
    target = approve(root, p)
    data = read(target)
    data["entries"][0]["cue"] = "Unreviewed edit"
    write(target, data)
    before = {f:f.read_bytes() for f in (root/"docs").iterdir()}
    with pytest.raises(ValueError, match="Unreviewed materialized"):
        integrate_reviewed(p, root)
    assert before == {f:f.read_bytes() for f in (root/"docs").iterdir()}


@pytest.mark.parametrize("reference", ["local:2#Head", "local:2#Missing", "local:99#Root"])
def test_self_missing_and_foreign_local_priors_rejected(packet, reference):
    root, p = packet
    choices(p, lambda d: d.update(reuse=[], changes=[{**explicit(), "prior": reference}]))
    with pytest.raises(ValueError):
        build(p, "2", root)


@pytest.mark.parametrize("decision,reference", [("hold", "new_offline_proposal"), ("retain_candidate", "local:2#Head")])
def test_held_local_root_and_cross_chapter_cycle_rejected(packet, decision, reference):
    root, p = packet
    manifest = read(p/"manifest.json")
    manifest["chapters"]["3"] = manifest["chapters"]["2"]
    write(p/"manifest.json", manifest)
    # Explicitly refresh the prepared evidence in this synthetic fixture only.
    write(p/"materialized/inventory2.json", materialize_inventory(p, "2", root))
    write(p/"author/decisions3.json", {"reuse": [], "changes": [{"term": "Root", "decision": decision, "prior": reference}]})
    choices(p, lambda d: d.update(reuse=[], changes=[{**explicit(), "prior": "local:3#Root"}]))
    with pytest.raises(ValueError):
        build(p, "2", root)


@pytest.mark.parametrize("decision", ["retain_candidate", "reuse_candidate"])
def test_missing_legacy_scope_can_be_explicitly_supplied_without_inventing_a_variant(packet, decision):
    root, p = packet
    path = root/"docs/chapter-1-cue-audit.json"
    data = read(path)
    data["entries"][0]["cue_scope"] = None
    write(path, data)
    write(p/"prior-freeze.json", {"docs/chapter-1-cue-audit.json": digest(path)})
    item = {**explicit(), "decision": decision, "prior": "docs/chapter-1-cue-audit.json#Head",
            "cue": "A literal head model.", "association_status": "unchanged_repeat", "change_origin": "existing_candidate_recount"}
    choices(p, lambda d: d.update(reuse=[], changes=[item]))
    e = build(p, "2", root)["entries"][0]
    assert e["legacy_scope_supplied"] is True and e["cue_scope"] == "Explicit actual head only."
    item["cue"] = "Changed legacy depiction"
    choices(p, lambda d: d.update(reuse=[], changes=[item]))
    with pytest.raises(ValueError, match="preserve cue/scope"):
        build(p, "2", root)
