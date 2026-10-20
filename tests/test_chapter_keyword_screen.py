"""Keyword-screen traceability only; PDF source review remains a separate check."""

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("chapter", range(20, 26))
def test_emphasized_keywords_have_explicit_cue_attempts(chapter):
    bank = json.loads((ROOT / f"docs/chapter-{chapter}-cue-audit.json").read_text())
    screen = bank["keyword_screen"]
    assert bank["keyword_screen_date"]
    assert screen["method"].strip()
    annotations = screen["highlight_annotation_check"]
    assert annotations["checked"] is True
    assert isinstance(annotations["highlight_annotations_found"], int)
    assert annotations["highlight_annotations_found"] >= 0
    assert annotations["note"].strip()
    entries = {e["term"].casefold(): e for e in bank["entries"]}
    assert screen["items"]
    seen = set()
    for item in screen["items"]:
        key = (item["term"].casefold(), item["pdf_page"])
        assert key not in seen
        seen.add(key)
        assert item["term"].strip() and item["emphasis"].strip()
        assert item["pdf_page"] in bank["source"]["pdf_pages"]
        assert item["page"] == item["pdf_page"] + bank["source"]["printed_page_offset"]
        target = item["entry_term"]
        if "#" in target:
            record, term = target.split("#", 1)
            path = (ROOT / record).resolve()
            assert path.parent == ROOT / "docs"
            assert path.name.startswith("chapter-") and path.name.endswith("-cue-audit.json")
            referenced = json.loads(path.read_text())
            entry = next(e for e in referenced["entries"] if e["term"].casefold() == term.casefold())
        else:
            entry = entries[target.casefold()]
        assert entry["decision"] in {"retain_candidate", "reuse_candidate", "hold"}
        assert entry["reason"].strip()
        if entry["decision"] != "hold":
            assert entry["cue"].strip()
    for excluded in screen["excluded_non_terms"]:
        assert excluded["description"].strip() and excluded["reason"].strip()
        assert excluded["pdf_page"] in bank["source"]["pdf_pages"]
