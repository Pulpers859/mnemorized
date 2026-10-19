"""Offline data-integrity checks, not pronunciation or mnemonic validation."""

from collections import Counter
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKSHOP_FILES = ("sound-bridge-workshop.json", "sound-bridge-workshop-2.json")
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


def load_workshop(filename):
    return json.loads((ROOT / "docs" / filename).read_text(encoding="utf-8"))


@pytest.fixture(scope="module", params=WORKSHOP_FILES, ids=WORKSHOP_FILES)
def workshop(request):
    return load_workshop(request.param)


@pytest.fixture(scope="module")
def all_workshops():
    # Missing integration data must fail, not silently skip a workshop's checks.
    return [load_workshop(filename) for filename in WORKSHOP_FILES]


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


def test_terms_are_unique_across_workshops_and_exclude_baseline(all_workshops):
    term_sets = [
        {normalized(entry["term"]) for entry in bank["entries"]}
        for bank in all_workshops
    ]
    seen = {normalized(term) for term in EXISTING_PHONETICS.values()}
    for filename, terms in zip(WORKSHOP_FILES, term_sets):
        assert not (seen & terms), f"Repeated terms in {filename}: {sorted(seen & terms)}"
        seen.update(terms)


def test_second_workshop_respects_frozen_bounds_and_exclusions(all_workshops):
    second = all_workshops[1]
    assert second["maximum_attempts"] == 60
    attempts = [attempt for entry in second["entries"] for attempt in entry["attempts"]]
    assert len(attempts) <= second["maximum_attempts"]
    assert all(count <= 20 for count in Counter(a["lane"] for a in attempts).values())
    excluded = {normalized(term) for term in second["excluded_terms"]}
    assert {normalized(e["term"]) for e in all_workshops[0]["entries"]} <= excluded
    assert not ({normalized(e["term"]) for e in second["entries"]} & excluded)


def test_only_retained_terms_get_new_canonical_phonetic_entries(all_workshops, catalog):
    phonetics = [entry for entry in catalog["entries"] if entry["kind"] == "phonetic"]
    by_id = {entry["id"]: entry for entry in phonetics}
    assert len(by_id) == len(phonetics), "Duplicate phonetic entry IDs"
    for entry_id, concept in EXISTING_PHONETICS.items():
        assert by_id[entry_id]["concept"] == concept

    # Exclude the pre-workshop baseline by identity, not by a hardcoded new count.
    new_entries = [entry for entry in phonetics if entry["id"] not in EXISTING_PHONETICS]
    retained = {
        entry["term"] for bank in all_workshops for entry in bank["entries"]
        if entry["decision"] == "retain_candidate"
    }
    assert {entry["concept"] for entry in new_entries} == retained
    assert len(new_entries) == len(retained), "Each retained term needs one primary entry"
    for entry in new_entries:
        assert entry["id"] == f"phonetic-{entry['concept']}"
        assert entry["status"] == "candidate"
        assert entry["evidence"] == {"render_audits": [], "recall_studies": []}


def test_held_and_rejected_terms_are_not_primary_catalog_concepts(all_workshops, catalog):
    excluded = {
        normalized(entry["term"]) for bank in all_workshops for entry in bank["entries"]
        if entry["decision"] in {"hold", "reject"}
    }
    primary_concepts = {
        normalized(entry["concept"]) for entry in catalog["entries"]
        if entry["id"] not in EXISTING_PHONETICS
    }
    assert not (excluded & primary_concepts), sorted(excluded & primary_concepts)
