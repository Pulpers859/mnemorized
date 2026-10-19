"""Chapter-bank data integrity only; not source, clinical or recall validation."""

from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_chapter_two_bank_is_bounded_and_explicitly_untested():
    bank = json.loads((ROOT / "docs/chapter-2-cue-audit.json").read_text())
    assert bank["chapter_id"] == "2"
    assert bank["production_admitted"] is False
    assert bank["source"]["pdf_pages"] == list(range(3, 10))
    assert len(bank["source"]["sha256"]) == 64
    entries = bank["entries"]
    assert len(entries) == len({e["term"].casefold() for e in entries}) == 16
    assert Counter(e["decision"] for e in entries) == {
        "retain_candidate": 12, "reuse_candidate": 1, "hold": 3,
    }
    for entry in entries:
        assert entry["tested"] is False
        assert entry["page"] in bank["source"]["pdf_pages"]
        assert entry["source_match"] in {"body", "heading", "heading_and_body"}
        assert entry["reason"].strip() and entry["prior"].strip()
        if entry["decision"] != "hold":
            assert isinstance(entry["cue"], str) and entry["cue"].strip()
    assert all(not evidence for evidence in bank["evidence"].values())
    assert all(value == 0 for value in bank["spend"].values())


def test_chapter_two_ledger_link_and_reused_cue():
    ledger = json.loads((ROOT / "docs/tintinalli-chapter-cue-ledger.json").read_text())
    record = next(r for r in ledger["subsequent_chapter_reviews"]
                  if r["chapter_id"] == "2")
    assert record["chapter_id"] == "2"
    assert (ROOT / record["record"]).is_file()
    assert (ROOT / record["report"]).is_file()
    assert int(ledger["next_chapter"]["chapter_id"]) >= 3
    bank = json.loads((ROOT / record["record"]).read_text())
    reused = [e for e in bank["entries"] if e["decision"] == "reuse_candidate"]
    assert [e["term"] for e in reused] == ["magnesium"]
    catalog = json.loads((ROOT / "docs/visual-cue-catalog.json").read_text())
    assert "magnesium-magnet" in {e["id"] for e in catalog["entries"]}
