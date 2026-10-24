"""Supplemental association record integrity, not semantic or recall validation."""

import json
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("span,chapters", [
    ("62-64", {62, 63, 64}), ("65-66", {65, 66}),
])
def test_second_look_preserves_provenance_and_declares_comparison(span, chapters):
    path = ROOT / f"docs/chapter-{span}-association-second-look.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(map(int, data["scope_chapters"])) == chapters
    assert data["status"] == "offline_untested"
    assert data["production_admitted"] is False
    assert data["evidence"] == {"render": [], "recall": []}
    assert (ROOT / data["independent_review"]).is_file()
    assert 1 <= len(data["entries"]) <= 15
    assert data["counts"]["entries"] == len(data["entries"])
    for field, count_key in (
        ("association_status", "association_classes"),
        ("selection_status", "selection_status"),
        ("change_origin", "change_origin"),
    ):
        assert data["counts"][count_key] == dict(Counter(e[field] for e in data["entries"]))
    seen = set()
    for entry in data["entries"]:
        chapter, term = int(entry["chapter"]), entry["term"]
        assert chapter in chapters
        key = (chapter, term.casefold())
        assert key not in seen
        seen.add(key)
        bank = json.loads((ROOT / f"docs/chapter-{chapter}-cue-audit.json").read_text(encoding="utf-8"))
        original = next(e for e in bank["entries"] if e["term"] == term)
        assert entry["original_decision"] == original["decision"]
        assert entry["original_prior"] == original.get("prior")
        assert entry["association_status"] in {
            "new_association", "meaningful_variant", "unchanged_repeat", "hold",
        }
        assert entry["selection_status"] in {"candidate", "hold"}
        assert entry["change_origin"] in {
            "existing_candidate_recount", "reconsidered_attempt", "new_revision",
        }
        if entry["selection_status"] == "candidate":
            assert entry["proposed_cue"]
        for field in ("encoded_scope", "why", "limitations"):
            assert entry[field]
        if entry["association_status"] != "hold":
            assert entry["proposed_cue"]
        assert entry["prior_evidence"]
        for reference in entry["prior_evidence"]:
            relative, anchor = reference.split("#", 1)
            target = (ROOT / relative).resolve()
            assert target.is_relative_to(ROOT / "docs")
            prior = json.loads(target.read_text(encoding="utf-8"))
            assert any(anchor in (e.get("term"), e.get("id")) for e in prior["entries"])
