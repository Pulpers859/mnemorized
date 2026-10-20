"""Revisit-register consistency, not clinical accuracy or mnemonic efficacy."""

import json

import pytest

from tools.chapter_cue_holds import ROOT, build_register, output_texts


def test_saved_hold_register_is_current_and_covers_all_banks():
    register = build_register()
    for path, expected in output_texts(register).items():
        assert (ROOT / path).read_text(encoding="utf-8") == expected
    assert register["chapters_checked"] == [str(i) for i in range(1, len(register["chapters_checked"]) + 1)]
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
