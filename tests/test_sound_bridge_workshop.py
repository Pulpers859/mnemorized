"""Offline data-integrity checks, not pronunciation or mnemonic validation."""

from collections import Counter
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EXISTING_PHONETICS = {
    "phonetic-carpal": "carpal",
    "phonetic-ataxia": "ataxia",
    "phonetic-rales": "rales",
    "phonetic-suture": "suture",
}
DECISIONS = {"retain_candidate", "hold", "reject"}
ATTEMPT_TEXT_FIELDS = (
    "lane", "term", "spoken_bridge", "pronunciation_caveat",
    "recognition_risk", "reason",
)


def normalized(term):
    return " ".join(term.split()).casefold()


def assert_text(value):
    assert isinstance(value, str) and value.strip(), repr(value)


@pytest.fixture(scope="module")
def workshop():
    return json.loads((ROOT / "docs" / "sound-bridge-workshop.json").read_text(
        encoding="utf-8"
    ))


@pytest.fixture(scope="module")
def catalog():
    return json.loads((ROOT / "docs" / "visual-cue-catalog.json").read_text(
        encoding="utf-8"
    ))


def test_workshop_term_records_are_unique_and_untested(workshop):
    entries = workshop["entries"]
    assert isinstance(entries, list) and entries
    terms = []
    for entry in entries:
        assert isinstance(entry, dict)
        assert_text(entry["term"])
        terms.append(normalized(entry["term"]))
        assert entry["decision"] in DECISIONS
        assert_text(entry["decision_reason"])
        assert isinstance(entry["independent_shortlist_review"], bool)
        assert entry["tested"] is False
    assert len(terms) == len(set(terms)), "Duplicate canonical workshop terms"


def test_workshop_attempt_fields_and_object_bounds(workshop):
    for entry in workshop["entries"]:
        attempts = entry["attempts"]
        assert isinstance(attempts, list) and attempts, entry["term"]
        for attempt in attempts:
            assert isinstance(attempt, dict), entry["term"]
            for field in ATTEMPT_TEXT_FIELDS:
                assert_text(attempt[field])
            assert normalized(attempt["term"]) == normalized(entry["term"])
            assert attempt["verdict"] in {"shortlist", "reject"}
            objects = attempt["objects"]
            assert isinstance(objects, list) and 1 <= len(objects) <= 2
            for obj in objects:
                assert_text(obj)
            assert isinstance(attempt["confusable_terms"], list)
            for term in attempt["confusable_terms"]:
                assert_text(term)


def test_workshop_summary_counts_are_derived_from_records(workshop):
    entries = workshop["entries"]
    attempts = [attempt for entry in entries for attempt in entry["attempts"]]
    decisions = Counter(entry["decision"] for entry in entries)
    assert type(workshop["attempt_count"]) is int
    assert workshop["attempt_count"] == len(attempts)
    assert type(workshop["unique_term_count"]) is int
    assert workshop["unique_term_count"] == len({
        normalized(entry["term"]) for entry in entries
    })
    assert set(workshop["decision_counts"]) == DECISIONS
    for decision, count in workshop["decision_counts"].items():
        assert type(count) is int
        assert count == decisions[decision]
    assert sum(workshop["decision_counts"].values()) == len(entries)


def test_only_retained_terms_get_new_canonical_phonetic_entries(workshop, catalog):
    phonetics = [entry for entry in catalog["entries"] if entry["kind"] == "phonetic"]
    by_id = {entry["id"]: entry for entry in phonetics}
    assert len(by_id) == len(phonetics), "Duplicate phonetic entry IDs"
    for entry_id, concept in EXISTING_PHONETICS.items():
        assert by_id[entry_id]["concept"] == concept

    # Exclude the pre-workshop baseline by identity, not by a hardcoded new count.
    new_entries = [entry for entry in phonetics if entry["id"] not in EXISTING_PHONETICS]
    retained = {
        entry["term"] for entry in workshop["entries"]
        if entry["decision"] == "retain_candidate"
    }
    assert {entry["concept"] for entry in new_entries} == retained
    assert len(new_entries) == len(retained), "Each retained term needs one primary entry"
    for entry in new_entries:
        assert entry["id"] == f"phonetic-{entry['concept']}"
        assert entry["status"] == "candidate"
        assert entry["evidence"] == {"render_audits": [], "recall_studies": []}


def test_held_and_rejected_terms_are_not_primary_catalog_concepts(workshop, catalog):
    excluded = {
        normalized(entry["term"]) for entry in workshop["entries"]
        if entry["decision"] in {"hold", "reject"}
    }
    primary_concepts = {
        normalized(entry["concept"]) for entry in catalog["entries"]
        if entry["id"] not in EXISTING_PHONETICS
    }
    assert not (excluded & primary_concepts), sorted(excluded & primary_concepts)
