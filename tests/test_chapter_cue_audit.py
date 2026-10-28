"""Chapter-bank data integrity only; not source, clinical or recall validation."""

from collections import Counter
import json
from pathlib import Path

import pytest

from tools.chapter_cue_holds import chapter_sort_key


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("chapter,start,end,offset", [
    (8, 17, 23, 18), (9, 23, 29, 18), (10, 29, 34, 18),
    (11, 1, 5, 52), (12, 5, 11, 52), (13, 11, 16, 52),
    (14, 16, 21, 52), (15, 21, 26, 52), (16, 26, 29, 52),
    (17, 29, 47, 52), (18, 47, 71, 52), (19, 71, 81, 52),
    (20, 81, 85, 52), (21, 85, 89, 52), (22, 1, 6, 142),
    (23, 7, 11, 142), (24, 11, 22, 142), (25, 22, 27, 142),
    (26, 27, 29, 142), (27, 30, 31, 142), (28, 31, 37, 142),
    ("29A", 37, 48, 142), ("29B", 48, 51, 142),
    (30, 52, 58, 142), (31, 59, 69, 142), (32, 70, 74, 142),
    (33, 74, 81, 142), (34, 81, 86, 142), (35, 1, 8, 228),
    (36, 8, 20, 228), (37, 20, 30, 228), (38, 31, 38, 228),
    (39, 1, 3, 266), (40, 3, 6, 266), (41, 6, 19, 266),
    (42, 19, 26, 266), (43, 26, 33, 266), (44, 33, 41, 266),
    (45, 41, 51, 266), (46, 51, 58, 266), (47, 58, 61, 266),
    (48, 1, 5, 328), (49, 6, 24, 328), (50, 24, 29, 328),
    (51, 29, 34, 328),
    (52, 34, 39, 328), (53, 39, 46, 328), (54, 46, 52, 328),
    (55, 52, 60, 328), (56, 61, 71, 328),
    (57, 71, 80, 328), (58, 80, 84, 328), (59, 84, 87, 328),
    (60, 87, 91, 328), (61, 92, 95, 328),
    (62, 1, 8, 424),
    (63, 8, 12, 424),
    (64, 12, 15, 424),
    (65, 15, 25, 424),
    (66, 25, 27, 424),
    (67, 27, 33, 424), (68, 33, 37, 424),
    (69, 37, 42, 424), (70, 43, 47, 424),
    (71, 1, 9, 472), (72, 9, 12, 472), (73, 12, 20, 472),
    (74, 20, 23, 472), (75, 23, 26, 472),
    (76, 26, 28, 472), (77, 28, 33, 472), (78, 33, 36, 472),
    (79, 36, 44, 472), (80, 44, 51, 472),
    (81, 51, 55, 472), (82, 55, 57, 472), (83, 58, 60, 472),
    (84, 60, 64, 472), (85, 64, 79, 472),
    (86, 79, 83, 472), (87, 83, 89, 472), (88, 1, 8, 562),
    (89, 8, 10, 562), (90, 11, 16, 562),
    (91, 16, 23, 562), (92, 24, 28, 562), (93, 29, 36, 562),
    (94, 36, 40, 562), (95, 40, 44, 562),
    (96, 1, 6, 606), (97, 6, 9, 606), (98, 9, 16, 606),
    (99, 16, 25, 606), (100, 25, 30, 606),
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
    source_files = {
        606: ("Tintin_OBGYN.pdf", "5a3a434223a4d8c18251cbd82c0ccbf7de448dbab8fb34ec1f09a76c15bc47f5"),
        562: ("Tintin_Renal_GU.pdf", "6e47e3801ced29aa53ad7be1024c0fd1f3ce20834078c1d6cc628db2885b7e67"),
        472: ("Tintin_GI.pdf", "f4b4343cf51073b2858b1e255d36f476e174083e54d5886fba8cdc67d391a915"),
        424: ("Tintin_Pulm.pdf", "cd8a5f5dade877d8e1daeb8411fedcac8862e9dfcb6256ce5d7fbc8d5c761ee6"),
        18: ("Tintin_Disaster Management.pdf", "9820446fab820addfcf4a3024439cc12aacba6279be29ed47e84361ca2ac4e82"),
        52: ("Tintin_Resuscitation.pdf", "d644c7ff121f44da8684b9c5cb3e0e69c5b66aa391dd5bcb9d5e4789023c3b69"),
        142: ("Tintin_Resuscitation Procedures.pdf", "93ace1119e1628b57d1f22b91fa0b9a3cab0e285086d423b8f033a5b5054e689"),
        228: ("Tintin_Analgesia_Anesthesia_Procedural Sedation.pdf", "dc0444f631bf8c0dc22c3a6d67cfce06f8e3945c6e019bb0a7b892c4b1e841fb"),
        266: ("Tintin_Wound Management.pdf", "691e464e103295d5b27bf4173a60fa6a86e81261cdeb35f2c9b45411ea4c8119"),
        328: ("Tintin_Cardiovascular.pdf", "53fb3bc68f3d15449fa1fe861a0c16831512d8e12fe9015e56ceda0830762fa6"),
    }
    assert (bank["source"]["file"], bank["source"]["sha256"].lower()) == source_files[offset]
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
        assert entry["source_match"] in {"body", "table", "heading_and_body", "heading", "table_and_body", "chapter_title", "box_title", "figure_label"}
        if entry["decision"] != "hold":
            assert entry["cue"].strip()
        if entry["decision"] == "reuse_candidate":
            assert (ROOT / entry["prior"].split("#")[0]).is_file()
    assert chapter_sort_key(ledger["next_chapter"]["chapter_id"]) > chapter_sort_key(str(chapter))
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
