"""Revisit-register consistency, not clinical accuracy or mnemonic efficacy."""

import json

import pytest

from tools.chapter_cue_holds import ROOT, build_register, chapter_sort_key, output_texts


def test_saved_hold_register_is_current_and_covers_all_banks():
    register = build_register()
    for path, expected in output_texts(register).items():
        assert (ROOT / path).read_text(encoding="utf-8") == expected
    ids = register["chapters_checked"]
    assert ids == sorted(ids, key=chapter_sort_key)
    numbers = {chapter_sort_key(chapter)[0] for chapter in ids}
    assert numbers == set(range(1, max(numbers) + 1))
    ledger = json.loads((ROOT / "docs/tintinalli-chapter-cue-ledger.json").read_text())
    reviewed_ids = {r["chapter_id"] for r in ledger["chapters"] + ledger["subsequent_chapter_reviews"]}
    assert set(register["chapters_checked"]) == reviewed_ids
    assert {e["term"] for e in register["active_holds"] if e["chapter_id"] == "1"} == {
        "Emergency Medical Services", "defibrillation", "naloxone", "opioid overdose",
    }
    assert not any(e["term"] == "sulfonylureas" for e in register["active_holds"])
    assert any(e["term"] == "sulfonylureas" for e in register["resolved_holds"])


def test_retained_elsewhere_does_not_silently_resolve_hold(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    for chapter, decision in [(1, "hold"), (2, "retain_candidate")]:
        bank = {"chapter_id": str(chapter), "title": "Example", "entries": [
            {"term": "same word", "page": 1, "decision": decision, "reason": "Revisit", "cue": None},
        ]}
        (docs / f"chapter-{chapter}-cue-audit.json").write_text(json.dumps(bank))
        (docs / f"chapter-{chapter}-cue-audit.md").write_text("Example")
    register = build_register(tmp_path)
    assert register["active_hold_occurrences"] == 1
    assert register["active_holds"][0]["retained_in_other_chapters"] == ["2"]
    assert not register["resolved_holds"]


def test_unknown_decision_cannot_silently_drop_a_term(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "chapter-1-cue-audit.md").write_text("Example")
    (docs / "chapter-1-cue-audit.json").write_text(json.dumps({
        "chapter_id": "1", "title": "Example", "entries": [
            {"term": "word", "page": 1, "decision": "typo"},
        ],
    }))
    with pytest.raises(ValueError, match="Unknown decision"):
        build_register(tmp_path)


def test_split_chapters_keep_individual_holds_in_source_order(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    for chapter in ["30", "29B", "28", "29A"]:
        bank = {"chapter_id": chapter, "title": "Example", "entries": [
            {"term": "same word", "page": 1, "decision": "hold", "reason": "Revisit", "cue": None},
        ]}
        (docs / f"chapter-{chapter}-cue-audit.json").write_text(json.dumps(bank))
        (docs / f"chapter-{chapter}-cue-audit.md").write_text("Example")
    register = build_register(tmp_path)
    assert register["chapters_checked"] == ["28", "29A", "29B", "30"]
    assert [entry["chapter_id"] for entry in register["active_holds"]] == ["28", "29A", "29B", "30"]
    assert register["active_hold_occurrences"] == 4
    assert register["unique_held_terms"] == 1


@pytest.mark.parametrize("chapter", ["", "0", "029A", "29a", "29AB", "../29A"])
def test_malformed_chapter_ids_are_rejected(chapter):
    with pytest.raises(ValueError, match="Invalid chapter ID"):
        chapter_sort_key(chapter)


def test_duplicate_split_chapter_ids_are_not_merged(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    bank = {"chapter_id": "29A", "title": "Example", "entries": []}
    for filename in ["chapter-29A-cue-audit.json", "chapter-copy-cue-audit.json"]:
        (docs / filename).write_text(json.dumps(bank))
    with pytest.raises(ValueError, match="Duplicate chapter ID"):
        build_register(tmp_path)


def test_separate_attempted_cue_is_preserved_for_a_held_term(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "chapter-1-cue-audit.md").write_text("Example")
    (docs / "chapter-1-cue-audit.json").write_text(json.dumps({
        "chapter_id": "1", "title": "Example", "entries": [
            {"term": "word", "page": 1, "decision": "hold", "cue": None,
             "attempted_cue": "A distinct attempted composition", "reason": "Revisit"},
        ],
    }))
    register = build_register(tmp_path)
    assert register["active_holds"][0]["attempted_cue"] == "A distinct attempted composition"
