"""Chapter-bank data integrity only; not source, clinical or recall validation."""

from collections import Counter
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("chapter,start,end,offset", [
    (8, 17, 23, 18), (9, 23, 29, 18), (10, 29, 34, 18),
    (11, 1, 5, 52), (12, 5, 11, 52), (13, 11, 16, 52),
])
def test_later_chapter_banks_are_consistent(chapter, start, end, offset):
    ledger = json.loads((ROOT / "docs/tintinalli-chapter-cue-ledger.json").read_text())
    record = next(r for r in ledger["subsequent_chapter_reviews"]
                  if r["chapter_id"] == str(chapter))
    bank = json.loads((ROOT / record["record"]).read_text())
    assert bank["chapter_id"] == str(chapter)
    assert (ROOT / record["report"]).is_file()
    assert bank["source"]["pdf_pages"] == list(range(start, end + 1))
    assert bank["source"]["printed_pages"] == list(range(start + offset, end + offset + 1))
    assert len(bank["source"]["sha256"]) == 64
    entries = bank["entries"]
    assert len(entries) == len({e["term"].casefold() for e in entries}) == record["selected_terms"]
    decisions = Counter(e["decision"] for e in entries)
    assert decisions["retain_candidate"] == record["new_candidates"]
    assert decisions["reuse_candidate"] == record["reused_candidates"]
    assert decisions["hold"] == record["holds"]
    assert set(decisions) <= {"retain_candidate", "reuse_candidate", "hold"}
    for entry in entries:
        assert entry["page"] == entry["pdf_page"] + bank["source"]["printed_page_offset"]
        assert entry["pdf_page"] in bank["source"]["pdf_pages"]
        assert entry["tested"] is False
        assert entry["cue_scope"].strip() and entry["reason"].strip()
        assert entry["source_match"] in {"body", "table", "heading_and_body", "heading"}
        if entry["decision"] != "hold":
            assert entry["cue"].strip()
        if entry["decision"] == "reuse_candidate":
            assert (ROOT / entry["prior"].split("#")[0]).is_file()
    assert int(ledger["next_chapter"]["chapter_id"]) >= chapter + 1
    assert bank["production_admitted"] is False
    assert all(not v for v in bank["evidence"].values())
    assert all(v == 0 for v in bank["spend"].values())


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


def test_chapter_six_bank_and_ledger_are_consistent():
    bank = json.loads((ROOT / "docs/chapter-6-cue-audit.json").read_text())
    ledger = json.loads((ROOT / "docs/tintinalli-chapter-cue-ledger.json").read_text())
    record = next(r for r in ledger["subsequent_chapter_reviews"]
                  if r["chapter_id"] == "6")
    assert bank["source"]["pdf_pages"] == list(range(7, 13))
    assert bank["source"]["printed_pages"] == list(range(25, 31))
    entries = bank["entries"]
    assert len(entries) == len({e["term"] for e in entries}) == 18
    assert Counter(e["decision"] for e in entries) == {
        "retain_candidate": 14, "reuse_candidate": 4,
    }
    assert record["new_candidates"] == 14 and record["reused_candidates"] == 4
    assert record["holds"] == 0
    sulfur = next(e for e in entries if e["term"] == "sulfonylureas")
    assert sulfur["prior"] == "user_example"
    assert sulfur["decision"] == "retain_candidate" and "eggs" in sulfur["cue"]
    assert (ROOT / record["record"]).is_file()
    assert (ROOT / record["report"]).is_file()
    for entry in entries:
        assert entry["page"] == entry["pdf_page"] + bank["source"]["printed_page_offset"]
        assert entry["pdf_page"] in bank["source"]["pdf_pages"]
        assert entry["tested"] is False
        assert entry["cue_scope"].strip() and entry["reason"].strip()
        assert entry["source_match"] in {"body", "table"}
        if entry["decision"] == "reuse_candidate":
            assert (ROOT / entry["prior"].split("#")[0]).is_file()
    assert set(bank["table_locations"]) == {
        e["term"] for e in entries if e["source_match"] == "table"
    }
    assert int(ledger["next_chapter"]["chapter_id"]) >= 7
    assert bank["production_admitted"] is False
    assert all(not v for v in bank["evidence"].values())
    assert all(v == 0 for v in bank["spend"].values())


def test_chapter_seven_bank_and_reuse_are_consistent():
    bank = json.loads((ROOT / "docs/chapter-7-cue-audit.json").read_text())
    ledger = json.loads((ROOT / "docs/tintinalli-chapter-cue-ledger.json").read_text())
    record = next(r for r in ledger["subsequent_chapter_reviews"]
                  if r["chapter_id"] == "7")
    assert bank["source"]["pdf_pages"] == list(range(12, 18))
    assert bank["source"]["printed_pages"] == list(range(30, 36))
    entries = bank["entries"]
    assert len(entries) == len({e["term"] for e in entries}) == 20
    assert Counter(e["decision"] for e in entries) == {
        "retain_candidate": 14, "reuse_candidate": 5, "hold": 1,
    }
    assert record["new_candidates"] == 14 and record["reused_candidates"] == 5
    assert record["holds"] == 1
    assert (ROOT / record["record"]).is_file()
    assert (ROOT / record["report"]).is_file()
    for entry in entries:
        assert entry["page"] == entry["pdf_page"] + bank["source"]["printed_page_offset"]
        assert entry["pdf_page"] in bank["source"]["pdf_pages"]
        assert entry["tested"] is False
        assert entry["cue_scope"].strip() and entry["reason"].strip()
        assert entry["source_match"] in {"body", "heading_and_body"}
        if entry["decision"] == "reuse_candidate":
            assert (ROOT / entry["prior"].split("#")[0]).is_file()
    assert int(ledger["next_chapter"]["chapter_id"]) >= 8
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
