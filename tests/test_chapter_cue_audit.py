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


def test_chapter_three_bank_and_ledger_are_consistent():
    bank = json.loads((ROOT / "docs/chapter-3-cue-audit.json").read_text())
    ledger = json.loads((ROOT / "docs/tintinalli-chapter-cue-ledger.json").read_text())
    record = next(r for r in ledger["subsequent_chapter_reviews"]
                  if r["chapter_id"] == "3")
    entries = bank["entries"]
    assert bank["chapter_id"] == "3"
    assert bank["source"]["pdf_pages"] == list(range(9, 14))
    assert len(entries) == len({e["term"] for e in entries}) == 16
    assert Counter(e["decision"] for e in entries) == {
        "retain_candidate": 14, "hold": 2,
    }
    assert record["retained_candidates"] == 14 and record["holds"] == 2
    assert (ROOT / record["record"]).is_file()
    assert (ROOT / record["report"]).is_file()
    assert int(ledger["next_chapter"]["chapter_id"]) >= 4
    for entry in entries:
        assert entry["tested"] is False
        assert entry["page"] in bank["source"]["pdf_pages"]
        assert entry["cue_scope"].strip() and entry["reason"].strip()
        assert entry["source_match"] in {"body", "table"}
    assert set(bank["table_locations"]) == {
        e["term"] for e in entries if e["source_match"] == "table"
    }
    assert bank["production_admitted"] is False
    assert all(not v for v in bank["evidence"].values())
    assert all(v == 0 for v in bank["spend"].values())


def test_chapter_four_bank_and_reuse_are_consistent():
    bank = json.loads((ROOT / "docs/chapter-4-cue-audit.json").read_text())
    ledger = json.loads((ROOT / "docs/tintinalli-chapter-cue-ledger.json").read_text())
    record = next(r for r in ledger["subsequent_chapter_reviews"]
                  if r["chapter_id"] == "4")
    entries = bank["entries"]
    assert bank["source"]["pdf_pages"] == list(range(13, 19))
    assert len(entries) == len({e["term"] for e in entries}) == 16
    assert Counter(e["decision"] for e in entries) == {
        "retain_candidate": 13, "reuse_candidate": 2, "hold": 1,
    }
    assert record["new_candidates"] == 13 and record["holds"] == 1
    assert record["reused_candidates"] == 2
    assert (ROOT / record["report"]).is_file()
    assert (ROOT / record["record"]).is_file()
    assert int(ledger["next_chapter"]["chapter_id"]) >= 5
    for entry in entries:
        assert entry["tested"] is False
        assert entry["page"] in bank["source"]["pdf_pages"]
        assert entry["cue_scope"].strip() and entry["reason"].strip()
        if entry["decision"] == "reuse_candidate":
            assert (ROOT / entry["prior"]).is_file()
    assert bank["production_admitted"] is False
    assert all(not v for v in bank["evidence"].values())
    assert all(v == 0 for v in bank["spend"].values())


def test_chapter_five_bank_maps_pdf_to_printed_pages():
    bank = json.loads((ROOT / "docs/chapter-5-cue-audit.json").read_text())
    ledger = json.loads((ROOT / "docs/tintinalli-chapter-cue-ledger.json").read_text())
    record = next(r for r in ledger["subsequent_chapter_reviews"]
                  if r["chapter_id"] == "5")
    assert bank["source"]["pdf_pages"] == list(range(1, 8))
    assert bank["source"]["printed_pages"] == list(range(19, 26))
    entries = bank["entries"]
    assert len(entries) == len({e["term"] for e in entries}) == 18
    assert Counter(e["decision"] for e in entries) == {
        "retain_candidate": 12, "reuse_candidate": 5, "hold": 1,
    }
    assert record["new_candidates"] == 12 and record["reused_candidates"] == 5
    assert record["holds"] == 1
    assert (ROOT / record["record"]).is_file()
    assert (ROOT / record["report"]).is_file()
    for entry in entries:
        assert entry["page"] == entry["pdf_page"] + 18
        assert entry["pdf_page"] in bank["source"]["pdf_pages"]
        assert entry["tested"] is False
        assert entry["cue_scope"].strip() and entry["reason"].strip()
        if entry["decision"] == "reuse_candidate":
            assert (ROOT / entry["prior"].split("#")[0]).is_file()
    assert int(ledger["next_chapter"]["chapter_id"]) >= 6
    assert bank["production_admitted"] is False
    assert all(not v for v in bank["evidence"].values())
    assert all(v == 0 for v in bank["spend"].values())
