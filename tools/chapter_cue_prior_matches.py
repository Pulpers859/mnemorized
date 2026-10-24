"""Report exact casefold term matches in earlier canonical banks, without writes."""

from __future__ import annotations

import argparse
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


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--before")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        report = find_prior_matches(args.bank, args.before, args.limit, root)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
