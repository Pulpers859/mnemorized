"""Read exact-term cue references; optionally restrict to earlier chapter banks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DECISIONS = {"retain_candidate", "reuse_candidate", "hold"}


def chapter_key(chapter: str) -> tuple[int, str]:
    match = re.fullmatch(r"([1-9][0-9]*)([A-Z]?)", str(chapter))
    if not match:
        raise ValueError(f"Invalid chapter ID: {chapter!r}")
    return int(match[1]), match[2]


def load_bank(path: Path, root: Path) -> tuple[Path, dict]:
    path = path.resolve()
    if not path.is_relative_to(root):
        raise ValueError("Bank path must remain inside root")
    bank = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(bank, dict) or not isinstance(bank.get("entries"), list):
        raise ValueError(f"Invalid bank structure: {path.name}")
    chapter_key(bank.get("chapter_id", ""))
    for entry in bank["entries"]:
        if (not isinstance(entry, dict) or not isinstance(entry.get("term"), str)
                or not entry["term"].strip() or entry.get("decision") not in DECISIONS):
            raise ValueError(f"Invalid term/decision in {path.name}")
    return path, bank


def find_prior_matches(bank: Path | str, before: str | None = None,
                       limit: int = 3, root: Path = ROOT) -> dict:
    root = root.resolve()
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("Limit must be a positive integer")
    path, query = load_bank(root / bank, root)
    cutoff = str(query["chapter_id"] if before is None else before)
    effective_before = min(cutoff, str(query["chapter_id"]), key=chapter_key)
    cutoff_key = chapter_key(effective_before)
    index = {}
    paths = (root / "docs").glob("chapter-*-cue-audit.json")
    candidates = []
    for prior_path in paths:
        match = re.fullmatch(r"chapter-([1-9][0-9]*[A-Z]?)-cue-audit\.json", prior_path.name)
        if match and chapter_key(match[1]) < cutoff_key and match[1] != str(query["chapter_id"]):
            candidates.append((chapter_key(match[1]), match[1], prior_path))
    for _, chapter, prior_path in sorted(candidates):
        prior_path, prior = load_bank(prior_path, root)
        if prior_path == path:
            continue
        if str(prior["chapter_id"]) != chapter:
            raise ValueError(f"Chapter ID does not match filename: {prior_path.name}")
        for entry in prior["entries"]:
            record = {"ref": prior_path.relative_to(root).as_posix() + "#" +
                      str(entry.get("id") or entry["term"]), "chapter_id": chapter,
                      "term": entry["term"], "decision": entry["decision"],
                      "cue": entry.get("cue"), "cue_scope": entry.get("cue_scope"),
                      "attempted_cue": entry.get("attempted_cue")}
            group = "held" if entry["decision"] == "hold" else "selected"
            index.setdefault(entry["term"].casefold(), {"selected": [], "held": []})[group].append(record)
    matches = []
    totals = {"selected": 0, "held": 0}
    for entry in query["entries"]:
        groups = index.get(entry["term"].casefold())
        if groups is None:
            continue
        counts = {name: len(records) for name, records in groups.items()}
        matches.append({"term": entry["term"], "current_decision": entry["decision"],
                        "human_review": entry["decision"] == "hold" and counts["selected"] > 0,
                        "total_match_counts": counts,
                        "earlier_selected": groups["selected"][:limit],
                        "earlier_held": groups["held"][:limit]})
        for name in totals:
            totals[name] += counts[name]
    return {"bank": path.relative_to(root).as_posix(), "before": cutoff,
            "effective_before": effective_before, "limit": limit,
            "matching": "term.casefold() equality only; human review determines cue decisions",
            "total_match_counts": totals, "matches": matches}


def find_term_matches(terms: list[str], before: str | None = None,
                      limit: int = 3, root: Path = ROOT) -> dict:
    """Read-only exact-term leads, grouping identical depictions/scopes once.

    Groups are content identities, not semantic equivalence or production approval.
    Held attempts remain separate even when their text matches a selected cue.
    """
    if (not isinstance(terms, list) or not terms
            or any(not isinstance(t, str) or not t.strip() for t in terms)):
        raise ValueError("Terms must be a nonempty list of nonempty strings")
    if type(limit) is not int or not 1 <= limit <= 8:
        raise ValueError("Limit must be an integer from 1 to 8")
    root = root.resolve()
    cutoff = chapter_key(before) if before is not None else None
    queries = list(dict.fromkeys(t.casefold() for t in terms))
    matches = {t: {"selected": {}, "held": {}, "blocked": {}} for t in queries}
    paths = []
    for path in (root / "docs").glob("chapter-*-cue-audit.json"):
        match = re.fullmatch(r"chapter-([1-9][0-9]*[A-Z]?)-cue-audit\.json", path.name)
        if match and (cutoff is None or chapter_key(match[1]) < cutoff):
            paths.append((chapter_key(match[1]), match[1], path))
    for _, chapter, path in sorted(paths):
        path, bank = load_bank(path, root)
        if str(bank["chapter_id"]) != chapter:
            raise ValueError(f"Chapter ID does not match filename: {path.name}")
        for entry in bank["entries"]:
            query = entry["term"].casefold()
            if query not in matches:
                continue
            held = entry["decision"] == "hold"
            cue = (entry.get("attempted_cue") or entry.get("cue")) if held else entry.get("cue")
            scope = entry.get("cue_scope")
            if any(v is not None and not isinstance(v, str) for v in (cue, scope)):
                raise ValueError(f"Invalid cue/scope in {path.name}: {entry['term']}")
            kind = "held" if held else "selected"
            if not held and any(entry.get(k) in ("hold", "restricted", "rejected")
                                for k in ("status", "selection_status")):
                kind = "blocked"
            key = cue, scope
            group = matches[query][kind].setdefault(key, {
                "cue_id": kind + "-" + hashlib.sha256(json.dumps(
                    key, ensure_ascii=True, separators=(",", ":")
                ).encode("utf-8")).hexdigest(),
                "cue": cue, "cue_scope": scope, "references": [],
                "requires_semantic_review": True,
                "missing_cue_or_scope": not cue or not scope,
            })
            group["references"].append({
                "ref": path.relative_to(root).as_posix() + "#" + str(entry.get("id") or entry["term"]),
                "term": entry["term"], "decision": entry["decision"],
                "reason": entry.get("reason"), "selection_status": entry.get("selection_status"),
                "status": entry.get("status"),
            })
    results = []
    for query, kinds in matches.items():
        result = {"term": query}
        for kind, grouped in kinds.items():
            groups = list(grouped.values())
            result[kind + "_group_count"] = len(groups)
            result[kind + "_record_count"] = sum(len(g["references"]) for g in groups)
            result[kind + "_groups_truncated"] = len(groups) > limit
            result[kind] = groups[:limit]
            for group in result[kind]:
                group["reference_count"] = len(group["references"])
                group["references_truncated"] = len(group["references"]) > limit
                group["references"] = group["references"][:limit]
        results.append(result)
    return {"matching": "Exact casefold term only; no stemming, aliases or clinical applicability inference.",
            "usage": "Offline unvalidated reference leads, never production approval. Groups deduplicate exact cue/scope text only. A miss is not proof of a cue gap. Read actual sources before changing meaning or scope.",
            "before": before, "limit": limit, "results": results}


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--bank", type=Path)
    source.add_argument("--term", action="append", help="Exact term lookup; repeat for a few actual Forge cue gaps")
    parser.add_argument("--before")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        report = (find_term_matches(args.term, args.before, args.limit, root)
                  if args.term is not None else find_prior_matches(args.bank, args.before, args.limit, root))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
