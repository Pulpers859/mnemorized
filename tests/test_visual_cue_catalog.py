"""Nonclinical, offline fixtures for the read-only cue catalog tool."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools import visual_cue_catalog as cue


@pytest.fixture
def catalog():
    return {
        "schema_version": 1,
        "usage": "Design candidates, not authority.",
        "sources": [{"id": "toy-source", "title": "Toy design notes"}],
        "entries": [{
            "id": "paper-kite", "concept": "flying paper", "aliases": ["kite"],
            "kind": "identity", "objects": ["paper kite"],
            "bridge": "A kite represents a flying toy.",
            "applicable_to": ["toy illustrations"], "not_for": ["weather forecasts"],
            "signature": "paper diamond on a string", "collision_tags": ["paper"],
            "status": "candidate",
            "provenance": {"origin": "original_design", "references": ["toy-source"]},
            "evidence": {"render_audits": [], "recall_studies": []},
        }],
    }


def test_valid_and_no_mutation(catalog, tmp_path):
    original = deepcopy(catalog)
    assert cue.validate_catalog(catalog, tmp_path) == []
    result = cue.search_catalog(catalog, "kite", root=tmp_path)
    assert result["results"][0]["entry"]["status"] == "candidate"
    assert catalog == original


@pytest.mark.parametrize("field,value", [
    ("id", "Not A Slug"), ("id", None), ("concept", " "), ("bridge", ""),
    ("signature", False), ("kind", "invented"), ("kind", []),
    ("status", "validated"), ("status", {}), ("objects", []),
    ("objects", ["one", "two", "three"]), ("objects", [""]),
    ("objects", "kite"), ("applicable_to", []), ("not_for", []),
    ("aliases", ["Kite", " kite "]), ("aliases", ["red kite", "red  kite"]),
    ("aliases", [1]), ("collision_tags", [""]),
    ("provenance", {"origin": "unknown", "references": []}),
    ("provenance", {"origin": [], "references": []}),
    ("provenance", {"origin": "legacy", "references": [], "extra": True}),
    ("evidence", {"render_audits": []}), ("evidence", []),
])
def test_invalid_entry_fields(catalog, tmp_path, field, value):
    catalog["entries"][0][field] = value
    assert cue.validate_catalog(catalog, tmp_path)


@pytest.mark.parametrize("mutation", [
    lambda c: c.update(schema_version=True),
    lambda c: c.update(schema_version=2),
    lambda c: c.update(usage=""),
    lambda c: c.update(extra="not allowed"),
    lambda c: c.pop("sources"),
    lambda c: c.update(entries={}),
    lambda c: c.update(sources={}),
    lambda c: c["entries"].append(None),
    lambda c: c["entries"][0].pop("signature"),
    lambda c: c["entries"][0].update(extra="not allowed"),
    lambda c: c["entries"].append(deepcopy(c["entries"][0])),
    lambda c: c["sources"].append(deepcopy(c["sources"][0])),
    lambda c: c["sources"].append("not an object"),
])
def test_invalid_catalog(catalog, tmp_path, mutation):
    mutation(catalog)
    assert cue.validate_catalog(catalog, tmp_path)
    with pytest.raises(cue.CatalogError):
        cue.search_catalog(catalog, "kite", root=tmp_path)


@pytest.mark.parametrize("value", [None, [], "text", 1])
def test_non_object_catalog(value, tmp_path):
    assert cue.validate_catalog(value, tmp_path)


@pytest.mark.parametrize("raw", [
    "{broken", '{"schema_version": 1, "schema_version": 1}',
    '{"x": NaN}', '{"x": Infinity}',
])
def test_malformed_json(tmp_path, raw):
    path = tmp_path / "catalog.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(cue.CatalogError):
        cue.load_catalog(path, tmp_path)
    assert path.read_text(encoding="utf-8") == raw


def test_missing_and_invalid_encoding(tmp_path):
    path = tmp_path / "absent.json"
    with pytest.raises(cue.CatalogError):
        cue.load_catalog(path, tmp_path)
    path.write_bytes(b"\xff")
    with pytest.raises(cue.CatalogError):
        cue.load_catalog(path, tmp_path)


@pytest.mark.parametrize("ref", [
    "missing.md", "../outside.md", "/outside.md", "C:/outside.md",
    "C:outside.md", "\\\\server\\share\\audit.md", "file:///outside.md",
    "https://example.org/audit", "toy-source", "folder/../../outside.md", "bad\x00path",
])
def test_evidence_requires_existing_internal_file(catalog, tmp_path, ref):
    catalog["entries"][0]["evidence"]["render_audits"] = [ref]
    assert cue.validate_catalog(catalog, tmp_path)


def test_evidence_and_provenance_do_not_promote(catalog, tmp_path):
    (tmp_path / "audit.md").write_text("Toy render audit", encoding="utf-8")
    entry = catalog["entries"][0]
    entry["evidence"] = {"render_audits": ["audit.md"], "recall_studies": ["audit.md"]}
    entry["provenance"]["references"] += ["audit.md", "https://example.org/design"]
    assert cue.validate_catalog(catalog, tmp_path) == []
    assert cue.search_catalog(catalog, "kite", root=tmp_path)["results"][0]["entry"]["status"] == "candidate"
    entry["provenance"]["references"].append("unknown-source")
    assert cue.validate_catalog(catalog, tmp_path)


@pytest.mark.parametrize("field", ["references", "render_audits", "recall_studies"])
@pytest.mark.parametrize("ref", [
    "Docs/Audits/Toy.md", "docs/Audits/Toy.md", "Docs/audits/Toy.md",
    "Docs/Audits/toy.md", "Docs/Audits/Toy.MD", "DOCS/AUDITS/TOY.MD",
])
def test_local_references_require_exact_component_case(catalog, tmp_path, field, ref):
    directory = tmp_path / "Docs" / "Audits"
    directory.mkdir(parents=True)
    audit = directory / "Toy.md"
    audit.write_text("Existence only; relevance is not validated.", encoding="utf-8")
    entry = catalog["entries"][0]
    section = entry["provenance"] if field == "references" else entry["evidence"]
    section[field] = [ref]
    before = deepcopy(catalog)

    errors = cue.validate_catalog(catalog, tmp_path)
    if ref == "Docs/Audits/Toy.md":
        assert errors == []
    else:
        assert any(field in error for error in errors)
    assert catalog == before
    assert audit.read_text(encoding="utf-8") == "Existence only; relevance is not validated."


def test_local_reference_lookup_errors_fail_closed(tmp_path, monkeypatch):
    audit = tmp_path / "audit.md"
    audit.write_text("Toy", encoding="utf-8")

    def inaccessible_directory(self):
        raise PermissionError("Directory listing unavailable")

    monkeypatch.setattr(Path, "iterdir", inaccessible_directory)
    assert cue._local_file("audit.md", tmp_path) is False


def test_directory_and_external_symlink_are_not_evidence(catalog, tmp_path):
    entry = catalog["entries"][0]
    entry["evidence"]["render_audits"] = ["."]
    assert cue.validate_catalog(catalog, tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside.write_text("external", encoding="utf-8")
    try:
        (tmp_path / "escape.txt").symlink_to(outside)
    except OSError:
        pytest.skip("Creating symlinks requires privileges on some Windows systems")
    entry["evidence"]["render_audits"] = ["escape.txt"]
    assert cue.validate_catalog(catalog, tmp_path)


def test_restricted_excluded_by_default(catalog, tmp_path):
    catalog["entries"][0]["status"] = "restricted"
    assert cue.search_catalog(catalog, "kite", root=tmp_path)["results"] == []
    result = cue.search_catalog(catalog, "kite", include_restricted=True, root=tmp_path)
    assert result["results"][0]["entry"]["status"] == "restricted"


@pytest.mark.parametrize("query", ["kite", "unrelated", "", "!!!"])
def test_safety_caveat_on_every_search(catalog, tmp_path, query):
    result = cue.search_catalog(catalog, query, root=tmp_path)
    assert result["status_caveat"] == cue.STATUS_CAVEAT
    assert "not clinical authority" in result["status_caveat"]
    assert "never automatically promote" in result["status_caveat"]
    if query != "kite":
        assert result["results"] == []


def test_weighted_ranking_ties_and_token_boundaries(catalog, tmp_path):
    base = catalog["entries"][0]
    catalog["entries"] = []
    for entry_id, field in [("z-alias", "aliases"), ("b-concept", "concept"),
                            ("a-concept", "concept"), ("bridge", "bridge")]:
        entry = deepcopy(base)
        entry.update(id=entry_id, concept="toy", aliases=[], bridge="design")
        entry[field] = ["kite"] if field == "aliases" else "kite"
        catalog["entries"].append(entry)
    result = cue.search_catalog(catalog, "KITE!", root=tmp_path)
    assert [item["entry"]["id"] for item in result["results"]] == [
        "z-alias", "a-concept", "b-concept", "bridge"]
    assert [item["score"] for item in result["results"]] == [4, 3, 3, 1]
    assert cue.search_catalog(catalog, "kites", root=tmp_path)["results"] == []
    assert len(cue.search_catalog(catalog, "kite", limit=1, root=tmp_path)["results"]) == 1


@pytest.mark.parametrize("limit", [0, 9, -1, True, 1.5, "2"])
def test_search_invalid_limits(catalog, tmp_path, limit):
    with pytest.raises(ValueError):
        cue.search_catalog(catalog, "kite", limit=limit, root=tmp_path)


def test_eight_result_cap(catalog, tmp_path):
    base = catalog["entries"][0]
    catalog["entries"] = [dict(deepcopy(base), id=f"kite-{i}") for i in range(10)]
    assert len(cue.search_catalog(catalog, "kite", root=tmp_path)["results"]) == 8


def test_cli_read_only(catalog, tmp_path, monkeypatch, capsys):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    before = {item: (item.read_bytes(), item.stat().st_mtime_ns) for item in tmp_path.iterdir()}
    monkeypatch.chdir(tmp_path)
    assert cue.main(["--catalog", str(path), "--query", "kite", "--validate", "--limit", "1"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["valid"] is True
    assert len(result["results"]) == 1
    assert result["status_caveat"] == cue.STATUS_CAVEAT
    assert cue.main(["--catalog", str(path), "--validate"]) == 0
    assert json.loads(capsys.readouterr().out)["entry_count"] == 1
    assert {item: (item.read_bytes(), item.stat().st_mtime_ns) for item in tmp_path.iterdir()} == before


@pytest.mark.parametrize("args", [[], ["--query", "kite", "--limit", "0"],
                                  ["--query", "kite", "--limit", "9"]])
def test_cli_argument_errors(args):
    with pytest.raises(SystemExit) as exc:
        cue.main(args)
    assert exc.value.code == 2


def test_cli_error_json_and_restriction_flag(catalog, tmp_path, capsys):
    path = tmp_path / "catalog.json"
    path.write_text("{bad", encoding="utf-8")
    assert cue.main(["--catalog", str(path), "--query", "kite"]) == 1
    assert json.loads(capsys.readouterr().out)["status_caveat"] == cue.STATUS_CAVEAT
    catalog["entries"][0]["status"] = "restricted"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    assert cue.main(["--catalog", str(path), "--query", "kite", "--include-restricted"]) == 0
    assert json.loads(capsys.readouterr().out)["results"][0]["entry"]["status"] == "restricted"


def test_default_catalog_is_repo_relative():
    assert cue.DEFAULT_CATALOG == Path(__file__).resolve().parents[1] / "docs" / "visual-cue-catalog.json"


def test_empty_catalog_and_no_semantic_inference(catalog, tmp_path):
    entry = catalog["entries"][0]
    entry.update(aliases=[], collision_tags=[], status="legacy_unverified")
    entry["provenance"]["references"] = []
    assert cue.validate_catalog(catalog, tmp_path) == []
    assert cue.search_catalog(catalog, "weather forecasts", root=tmp_path)["results"] == []
    assert cue.search_catalog(catalog, "kite", root=tmp_path)["results"][0]["entry"]["status"] == "legacy_unverified"
    catalog["entries"] = []
    catalog["sources"] = []
    assert cue.validate_catalog(catalog, tmp_path) == []
    assert cue.search_catalog(catalog, "kite", root=tmp_path)["results"] == []


def test_canonical_catalog_validates_with_only_portable_docs_dependencies(tmp_path, monkeypatch):
    """Use the real catalog, never ignored workstation evidence or invented data.

    This canonical-data policy is intentionally narrower than the generic schema:
    local references ship under docs/. No Git or remote lookup is needed.
    """
    raw = cue.DEFAULT_CATALOG.read_bytes()
    catalog = json.loads(raw)
    source_ids = {source["id"] for source in catalog["sources"]}
    local_refs = set()
    for entry in catalog["entries"]:
        for ref in entry["provenance"]["references"]:
            if ref not in source_ids and not ref.startswith(("http://", "https://")):
                local_refs.add(ref)
        for refs in entry["evidence"].values():
            local_refs.update(refs)

    for ref in sorted(local_refs):
        parts = ref.split("/")
        assert parts[0] == "docs" and len(parts) > 1, (
            f"Canonical reference must ship under docs/, not depend on local evidence: {ref}"
        )
        assert all(part not in {"", ".", ".."} for part in parts), ref
        assert "\\" not in ref and ":" not in ref, ref
        source = cue.REPO_ROOT
        for part in parts:
            # Windows is case-insensitive; CI and other checkouts need exact casing.
            assert part in {child.name for child in source.iterdir()}, ref
            source = source / part
            assert not source.is_symlink(), f"Canonical reference cannot depend on a symlink: {ref}"
        assert source.is_file(), ref
        destination = tmp_path.joinpath(*parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    path = tmp_path / "docs" / "visual-cue-catalog.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    monkeypatch.chdir(tmp_path)
    actual = cue.load_catalog(path, root=tmp_path)
    assert actual == catalog
    assert cue.DEFAULT_CATALOG.read_bytes() == raw
    result = cue.search_catalog(actual, "clock", root=tmp_path)
    assert result["status_caveat"] == cue.STATUS_CAVEAT
    assert all(item["entry"]["status"] != "restricted" for item in result["results"])
