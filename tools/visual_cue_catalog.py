"""Offline validation and literal search of visual design candidates (stdlib only)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PureWindowsPath
import re
import sys
from urllib.parse import urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = REPO_ROOT / "docs" / "visual-cue-catalog.json"
STATUS_CAVEAT = (
    "Design candidates only, not clinical authority. Candidate and legacy_unverified "
    "entries are unvalidated; restricted entries require explicit inclusion. "
    "References and evidence never automatically promote status. Literal token "
    "matches do not establish clinical applicability; no missing cues are auto-filled."
)
ENTRY_FIELDS = {
    "id", "concept", "aliases", "kind", "objects", "bridge", "applicable_to",
    "not_for", "signature", "collision_tags", "status", "provenance", "evidence",
}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class CatalogError(ValueError):
    """The catalog cannot be safely used."""


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _local_file(value: str, root: Path) -> bool:
    # Reject foreign path syntaxes before any filesystem lookup.
    windows = PureWindowsPath(value)
    path = Path(value)
    if (not value.strip() or "\\" in value or ":" in value or "\x00" in value
            or windows.drive or windows.root or path.is_absolute()
            or ".." in path.parts):
        return False
    try:
        resolved = (root / path).resolve()
        resolved.relative_to(root.resolve())
        # is_file() alone accepts incorrectly cased names on Windows.
        parent = root
        for part in path.parts:
            if not any(child.name == part for child in parent.iterdir()):
                return False
            parent = parent / part
        return resolved.is_file()
    except (OSError, ValueError, RuntimeError):
        return False


def _web_reference(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


def validate_catalog(catalog: object, root: Path = REPO_ROOT) -> list[str]:
    """Return schema/reference errors without changing data or opening evidence files.

    Sources are metadata objects with unique slug IDs; their remaining metadata is
    intentionally unconstrained. Entry and nested entry objects use exact fields.
    """
    errors: list[str] = []

    def fields(value: object, required: set[str], label: str) -> bool:
        if not isinstance(value, dict):
            errors.append(f"{label}: expected object")
            return False
        missing = required - value.keys()
        extra = value.keys() - required
        if missing:
            errors.append(f"{label}: missing fields {sorted(missing)}")
        if extra:
            errors.append(f"{label}: extra fields {sorted(extra)}")
        return True

    def strings(value: object, label: str, minimum: int = 0, maximum: int | None = None) -> bool:
        if not isinstance(value, list):
            errors.append(f"{label}: expected list of nonempty strings")
            return False
        valid = all(_text(item) for item in value)
        if not valid or len(value) < minimum or (maximum is not None and len(value) > maximum):
            errors.append(f"{label}: expected nonempty strings, length {minimum}..{maximum or 'unbounded'}")
            return False
        return True

    if not fields(catalog, {"schema_version", "usage", "sources", "entries"}, "catalog"):
        return errors
    if type(catalog.get("schema_version")) is not int or catalog["schema_version"] != 1:
        errors.append("schema_version: expected integer 1")
    if not _text(catalog.get("usage")):
        errors.append("usage: expected nonempty string")
    source_ids: set[str] = set()
    sources = catalog.get("sources")
    if not isinstance(sources, list):
        errors.append("sources: expected list")
    else:
        for index, source in enumerate(sources):
            source_id = source.get("id") if isinstance(source, dict) else None
            if not isinstance(source_id, str) or not SLUG.fullmatch(source_id):
                errors.append(f"sources[{index}].id: expected slug")
            elif source_id in source_ids:
                errors.append(f"sources[{index}].id: duplicate ID {source_id}")
            else:
                source_ids.add(source_id)
    entries = catalog.get("entries")
    if not isinstance(entries, list):
        errors.append("entries: expected list")
        return errors
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"entries[{index}]"
        if not fields(entry, ENTRY_FIELDS, label):
            continue
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not SLUG.fullmatch(entry_id):
            errors.append(f"{label}.id: expected slug")
        elif entry_id in seen:
            errors.append(f"{label}.id: duplicate ID {entry_id}")
        else:
            seen.add(entry_id)
        for name in ("concept", "bridge", "signature"):
            if not _text(entry.get(name)):
                errors.append(f"{label}.{name}: expected nonempty string")
        for name, allowed in (
            ("kind", {"identity", "state", "relationship", "phonetic", "composition"}),
            ("status", {"candidate", "legacy_unverified", "restricted"}),
        ):
            if not isinstance(entry.get(name), str) or entry[name] not in allowed:
                errors.append(f"{label}.{name}: invalid value")
        for name in ("aliases", "objects", "applicable_to", "not_for", "collision_tags"):
            minimum = 1 if name in {"objects", "applicable_to", "not_for"} else 0
            if strings(entry.get(name), f"{label}.{name}", minimum, 2 if name == "objects" else None):
                if name == "aliases":
                    aliases = [" ".join(alias.split()).casefold() for alias in entry[name]]
                    if len(set(aliases)) != len(aliases):
                        errors.append(f"{label}.aliases: duplicate aliases")
        provenance = entry.get("provenance")
        if fields(provenance, {"origin", "references"}, f"{label}.provenance"):
            origin = provenance.get("origin")
            if not isinstance(origin, str) or origin not in {"legacy", "original_design", "user_example"}:
                errors.append(f"{label}.provenance.origin: invalid value")
            if strings(provenance.get("references"), f"{label}.provenance.references"):
                for ref in provenance["references"]:
                    if ref not in source_ids and not _web_reference(ref) and not _local_file(ref, root):
                        errors.append(f"{label}.provenance.references: unknown source or invalid file {ref!r}")
        evidence = entry.get("evidence")
        if fields(evidence, {"render_audits", "recall_studies"}, f"{label}.evidence"):
            for name in ("render_audits", "recall_studies"):
                if strings(evidence.get(name), f"{label}.evidence.{name}"):
                    for ref in evidence[name]:
                        if not _local_file(ref, root):
                            errors.append(f"{label}.evidence.{name}: invalid repository file {ref!r}")
    return errors


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise CatalogError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise CatalogError(f"Invalid JSON constant: {value}")


def load_catalog(path: Path = DEFAULT_CATALOG, root: Path = REPO_ROOT) -> dict:
    try:
        with Path(path).open(encoding="utf-8") as handle:
            catalog = json.load(handle, object_pairs_hook=_unique_object,
                                parse_constant=_invalid_constant)
    except (OSError, UnicodeError, ValueError) as exc:
        raise CatalogError(f"Cannot load catalog: {exc}") from exc
    errors = validate_catalog(catalog, root)
    if errors:
        raise CatalogError("; ".join(errors))
    return catalog


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[^\W_]+", text.casefold()))


def search_catalog(catalog: dict, query: str, limit: int = 8,
                   include_restricted: bool = False, root: Path = REPO_ROOT) -> dict:
    if type(limit) is not int or not 1 <= limit <= 8:
        raise ValueError("limit must be an integer from 1 to 8")
    if not isinstance(query, str):
        raise ValueError("query must be a string")
    errors = validate_catalog(catalog, root)
    if errors:
        raise CatalogError("; ".join(errors))
    tokens = _tokens(query)
    ranked = []
    for entry in catalog["entries"]:
        if entry["status"] == "restricted" and not include_restricted:
            continue
        aliases = _tokens(" ".join(entry["aliases"]))
        score = (4 * len(tokens & aliases) + 3 * len(tokens & _tokens(entry["concept"]))
                 + len(tokens & _tokens(entry["bridge"])))
        if score:
            ranked.append((score, entry))
    ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
    return {
        "query": query, "status_caveat": STATUS_CAVEAT,
        "include_restricted": include_restricted,
        "results": [{"score": score, "entry": entry} for score, entry in ranked[:limit]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--query")
    parser.add_argument("--limit", type=int, choices=range(1, 9), default=8)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--include-restricted", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate and args.query is None:
        parser.error("provide --validate or --query")
    try:
        catalog = load_catalog(args.catalog)
        if args.query is not None:
            output = search_catalog(catalog, args.query, args.limit, args.include_restricted)
            if args.validate:
                output["valid"] = True
        else:
            output = {"valid": True, "entry_count": len(catalog["entries"]),
                      "status_caveat": STATUS_CAVEAT}
    except CatalogError as exc:
        print(json.dumps({"valid": False, "error": str(exc), "status_caveat": STATUS_CAVEAT}))
        return 1
    print(json.dumps(output, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
