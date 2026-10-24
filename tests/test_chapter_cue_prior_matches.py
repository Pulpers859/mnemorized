"""Exact prior-record retrieval and read-only behavior; no cue adjudication."""

import json

import pytest

from tools.chapter_cue_prior_matches import find_prior_matches, main


def bank(root, chapter, entries):
    path = root / "docs" / f"chapter-{chapter}-cue-audit.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"chapter_id": str(chapter), "entries": entries}), encoding="utf-8")
    return path


def entry(term="Stra\u00dfe", decision="retain_candidate", **fields):
    return {"term": term, "decision": decision, "cue": "source cue",
            "cue_scope": "source scope", **fields}


def test_casefold_finds_selected_for_current_hold_without_rewriting(tmp_path, capsys):
    prior = bank(tmp_path, 1, [entry(id="root-one"), entry("another", "reuse_candidate")])
    query = bank(tmp_path, 2, [entry("STRASSE", "hold"), entry("unmatched", "hold")])
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert main(["--bank", str(query)], root=tmp_path) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["before"] == "2"
    assert report["effective_before"] == "2"
    assert len(report["matches"]) == 1
    result = report["matches"][0]
    assert result["human_review"] is True
    assert result["current_decision"] == "hold"
    assert result["total_match_counts"] == {"selected": 1, "held": 0}
    record = result["earlier_selected"][0]
    assert record["ref"] == "docs/chapter-1-cue-audit.json#root-one"
    assert record["cue"] == "source cue" and record["cue_scope"] == "source scope"
    assert record["decision"] == "retain_candidate"
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
    assert prior.is_file()


def test_same_bank_and_future_excluded_and_explicit_cutoff(tmp_path):
    bank(tmp_path, 1, [entry()])
    query = bank(tmp_path, 2, [entry()])
    bank(tmp_path, 3, [entry()])
    report = find_prior_matches(query, root=tmp_path)
    assert report["total_match_counts"] == {"selected": 1, "held": 0}
    earlier = find_prior_matches(query, before="1", root=tmp_path)
    assert earlier["matches"] == [] and earlier["effective_before"] == "1"
    # A later requested cutoff cannot admit the query chapter or future chapters.
    report = find_prior_matches(query, before="4", root=tmp_path)
    assert report["before"] == "4" and report["effective_before"] == "2"
    assert [r["chapter_id"] for r in report["matches"][0]["earlier_selected"]] == ["1"]


def test_limits_are_per_group_but_counts_include_all_matches(tmp_path):
    for chapter in range(1, 9):
        decision = "hold" if chapter % 2 else "reuse_candidate"
        bank(tmp_path, chapter, [entry(decision=decision, attempted_cue="source attempt")])
    query = bank(tmp_path, 9, [entry(decision="hold")])
    report = find_prior_matches(query, limit=2, root=tmp_path)
    result = report["matches"][0]
    assert report["total_match_counts"] == result["total_match_counts"] == {"selected": 4, "held": 4}
    assert [r["chapter_id"] for r in result["earlier_selected"]] == ["2", "4"]
    assert [r["chapter_id"] for r in result["earlier_held"]] == ["1", "3"]
    assert result["earlier_held"][0]["attempted_cue"] == "source attempt"
    assert all(r["decision"] == "hold" for r in result["earlier_held"])
    assert len(find_prior_matches(query, root=tmp_path)["matches"][0]["earlier_selected"]) == 3


def test_split_ids_sort_naturally_and_held_is_not_selected(tmp_path):
    for chapter in ["30", "29B", "28", "29A"]:
        bank(tmp_path, chapter, [entry(decision="hold")])
    query = bank(tmp_path, 31, [entry(decision="hold")])
    result = find_prior_matches(query, limit=5, root=tmp_path)["matches"][0]
    assert [r["chapter_id"] for r in result["earlier_held"]] == ["28", "29A", "29B", "30"]
    assert result["earlier_selected"] == [] and result["human_review"] is False
    report = find_prior_matches(query, before="29B", root=tmp_path)
    assert report["effective_before"] == "29B"
    assert [r["chapter_id"] for r in report["matches"][0]["earlier_held"]] == ["28", "29A"]


def test_no_stemming_whitespace_normalization_or_aliases(tmp_path):
    bank(tmp_path, 1, [entry("cat"), entry(" pain"), entry("alias")])
    query = bank(tmp_path, 2, [entry("cats"), entry("pain"), entry("different", prior="alias")])
    assert find_prior_matches(query, root=tmp_path)["matches"] == []


def test_outside_root_is_rejected(tmp_path):
    root = tmp_path / "inside"
    root.mkdir()
    outside = bank(tmp_path, 1, [])
    with pytest.raises(ValueError, match="inside root"):
        find_prior_matches(outside, root=root)


@pytest.mark.parametrize("limit,before", [(0, None), (-1, None), (3, "29a"), (3, "../1")])
def test_invalid_arguments(tmp_path, limit, before):
    query = bank(tmp_path, 2, [])
    with pytest.raises(ValueError):
        find_prior_matches(query, before=before, limit=limit, root=tmp_path)


@pytest.mark.parametrize("payload", [{}, {"chapter_id": "2", "entries": [entry(decision="typo")]},
                                    {"chapter_id": "bad", "entries": []}])
def test_invalid_bank(tmp_path, payload):
    query = bank(tmp_path, 2, [])
    query.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        find_prior_matches(query, root=tmp_path)


def test_cli_validation_is_nonzero(tmp_path, capsys):
    query = bank(tmp_path, 2, [])
    with pytest.raises(SystemExit) as exc:
        main(["--bank", str(query), "--limit", "0"], root=tmp_path)
    assert exc.value.code == 2
    assert "positive integer" in capsys.readouterr().err
