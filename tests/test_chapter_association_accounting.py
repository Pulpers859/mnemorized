"""Reporting integrity for new chapter banks, not mnemonic effectiveness."""

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("chapter", range(67, 74))
def test_new_banks_separate_association_selection_and_origin(chapter):
    bank = json.loads((ROOT / f"docs/chapter-{chapter}-cue-audit.json").read_text(encoding="utf-8"))
    for entry in bank["entries"]:
        assert entry["association_status"] in {
            "new_association", "meaningful_variant", "unchanged_repeat", "hold",
        }
        assert entry["selection_status"] == (
            "hold" if entry["decision"] == "hold" else "candidate"
        )
        assert (entry["association_status"] == "hold") == (entry["decision"] == "hold")
        assert entry["change_origin"] in {
            "new_proposal", "existing_candidate_recount", "reconsidered_attempt", "new_revision",
        }
        if entry["association_status"] == "unchanged_repeat":
            assert entry["change_origin"] in {"existing_candidate_recount", "reconsidered_attempt"}
        if entry["association_status"] == "meaningful_variant":
            assert entry["change_origin"] in {"new_revision", "reconsidered_attempt"}
        comparison = entry["association_comparison"]
        if isinstance(comparison, str):
            assert comparison.strip()
        else:
            assert isinstance(comparison, dict)
            assert comparison["universe"].strip() and comparison["reason"].strip()
        if entry["decision"] == "hold":
            assert entry["reason"].strip()
        else:
            assert entry["cue"].strip() and entry["cue_scope"].strip()
        if entry["decision"] == "reuse_candidate":
            relative, anchor = entry["prior"].split("#", 1)
            target = (ROOT / relative).resolve()
            assert target.parent == ROOT / "docs"
            prior = json.loads(target.read_text(encoding="utf-8"))
            matches = [e for e in prior["entries"] if anchor.casefold() in {
                str(e.get("term", "")).casefold(), str(e.get("id", "")).casefold(),
            }]
            assert len(matches) == 1
            assert matches[0].get("decision") != "hold"
            assert matches[0].get("selection_status") != "hold"
            assert matches[0].get("status") != "restricted"
