"""Build the offline revisit register from current chapter decisions, without APIs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = Path("docs/tintinalli-held-cues.json")
MD_PATH = Path("docs/tintinalli-held-cues.md")
DECISIONS = {"hold", "retain_candidate", "reuse_candidate"}


def chapter_sort_key(chapter: str) -> tuple[int, str]:
    """Preserve split source IDs such as 29A and 29B in textbook order."""
    match = re.fullmatch(r"([1-9][0-9]*)([A-Z]?)", str(chapter))
    if not match:
        raise ValueError(f"Invalid chapter ID: {chapter!r}")
    return int(match[1]), match[2]


def build_register(root: Path = ROOT) -> dict:
    banks = []
    for path in (root / "docs").glob("chapter-*-cue-audit.json"):
        # Chapter IDs, not file ordering, determine the register order.
        bank = json.loads(path.read_text(encoding="utf-8"))
        chapter = str(bank["chapter_id"])
        chapter_sort_key(chapter)
        banks.append((chapter, path, bank))
    banks.sort(key=lambda item: chapter_sort_key(item[0]))
    ids = [item[0] for item in banks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chapter ID in current cue banks")
    active, resolved, retained = [], [], {}
    for chapter, path, bank in banks:
        source = path.relative_to(root).as_posix()
        report = bank.get("report", f"docs/chapter-{chapter}-cue-audit.md")
        if not (root / report).is_file():
            raise ValueError(f"Missing chapter report: {report}")
        entries = bank["entries"]
        terms = {e["term"].casefold(): e for e in entries}
        if len(terms) != len(entries):
            raise ValueError(f"Duplicate term in {source}")
        for entry in entries:
            decision = entry["decision"]
            if decision not in DECISIONS:
                raise ValueError(f"Unknown decision in {source}: {decision}")
            if decision != "hold":
                retained.setdefault(entry["term"].casefold(), []).append(str(chapter))
                continue
            active.append({
                "chapter_id": str(chapter), "chapter_title": bank["title"],
                "term": entry["term"], "printed_page": entry["page"],
                "source_record": source, "report": report,
                "attempted_cue": entry.get("attempted_cue") or entry.get("cue"),
                "reason": entry["reason"],
            })
        for history in bank.get("resolved_holds", []):
            term = history["term"]
            entry = terms[term.casefold()]
            if entry["decision"] == "hold":
                raise ValueError(f"Resolved term still held in {source}: {term}")
            resolved.append({
                "chapter_id": str(chapter), "term": term,
                "source_record": source, "report": report,
                "current_decision": entry["decision"],
                "resolution": history["resolution"],
            })
    for entry in active:
        entry["retained_in_other_chapters"] = retained.get(entry["term"].casefold(), [])
    return {
        "schema_version": 1,
        "scope": "Current chapter holds, not rejected sound-workshop terms or exhaustive textbook vocabulary. Historical resolutions are explicit, never inferred from another chapter.",
        "chapters_checked": [str(i) for i in ids],
        "active_hold_occurrences": len(active),
        "unique_held_terms": len({e["term"].casefold() for e in active}),
        "active_holds": active, "resolved_holds": resolved,
    }


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(register: dict) -> str:
    lines = [
        "# Tintinalli Held-Cue Revisit List", "",
        "Generated from current structured chapter banks; do not edit this snapshot by hand.",
        "Update the chapter decision, then run `python tools/chapter_cue_holds.py --write`.",
        "`--check` detects stale snapshots; focused tests enforce this on future batches.", "",
        f"Active: **{register['active_hold_occurrences']} chapter holds / {register['unique_held_terms']} unique terms**.",
        "Chapters checked: " + ", ".join(register["chapters_checked"]) + ".", "",
        "A hold means revisit the proposal, not that the term cannot have a good cue.",
        "The reasons are preserved editorial judgments, not new clinical or learning evidence.",
        "Earlier holds are not erased when another chapter retains a cue. Resolutions below",
        "are explicit decisions. Workshop-wide rejected/held words remain in their separate",
        "sound-bridge banks; this register covers all reviewed chapter banks.", "",
        "## Active Holds", "",
        "| Chapter / Page | Term | Attempted Cue | Why Held | Review |",
        "|---|---|---|---|---|",
    ]
    for entry in register["active_holds"]:
        reason = entry["reason"]
        if entry["retained_in_other_chapters"]:
            reason += " Retained elsewhere: Chapter " + ", ".join(entry["retained_in_other_chapters"]) + "; revisit discrepancy."
        lines.append("| " + " | ".join([
            f"{entry['chapter_id']} / {entry['printed_page']}", _cell(entry["term"]),
            _cell(entry["attempted_cue"] or "None proposed"), _cell(reason),
            f"[Review]({Path(entry['report']).name})",
        ]) + " |")
    lines += ["", "## Resolved Holds", "",
              "Preserved history, not active revisit items or empirical validation.", "",
              "| Chapter | Term | Resolution | Review |", "|---|---|---|---|"]
    for entry in register["resolved_holds"]:
        lines.append(f"| {entry['chapter_id']} | {_cell(entry['term'])} | {_cell(entry['resolution'])} | [Review]({Path(entry['report']).name}) |")
    return "\n".join(lines) + "\n"


def output_texts(register: dict) -> dict[Path, str]:
    return {JSON_PATH: json.dumps(register, indent=2, ensure_ascii=True) + "\n",
            MD_PATH: render_markdown(register)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = output_texts(build_register())
    stale = []
    for relative, content in outputs.items():
        path = ROOT / relative
        if args.write:
            path.write_text(content, encoding="utf-8")
        elif not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(relative.as_posix())
    if stale:
        print("Stale hold register: " + ", ".join(stale))
        return 1
    print("Hold register " + ("updated" if args.write else "current"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
