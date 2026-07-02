#!/usr/bin/env python3
"""Build local visual QA packs from exported Mnemorized forge bundles."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PASS_THRESHOLD = 85


@dataclass
class Finding:
    severity: str
    code: str
    message: str


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()
    return slug[:80] or "visual_qa_pack"


def read_bundle(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not data.get("story"):
        raise ValueError(f"{path} does not look like a forge bundle.")
    return data


def bundle_paths(inputs: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for item in inputs:
        if item.is_dir():
            paths.extend(sorted(item.rglob("*_bundle.json")))
        elif item.is_file():
            paths.append(item)
        else:
            raise FileNotFoundError(item)
    return paths


def words(text: str) -> list[str]:
    return re.findall(r"\S+", text or "")


def quoted_segments(text: str) -> list[str]:
    return re.findall(r'"([^"]+)"', text or "")


def anchor_lines(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return list(bundle.get("story", {}).get("voLines") or [])


def image_prompts(bundle: dict[str, Any]) -> dict[str, str]:
    prompts = bundle.get("image_prompts") or {}
    return {
        "prompt1": str(prompts.get("prompt1") or ""),
        "prompt2": str(prompts.get("prompt2") or ""),
    }


def audit_bundle(bundle: dict[str, Any]) -> tuple[int, list[Finding]]:
    findings: list[Finding] = []
    anchors = anchor_lines(bundle)
    prompts = image_prompts(bundle)
    prompt2 = prompts["prompt2"]

    if not 8 <= len(anchors) <= 10:
        findings.append(Finding("major", "anchor_count", f"Expected 8-10 anchors; found {len(anchors)}."))

    hook_count = sum(1 for anchor in anchors if str(anchor.get("hook") or "").strip())
    if hook_count < len(anchors):
        findings.append(Finding("major", "missing_hooks", f"{len(anchors) - hook_count} anchors do not include HOOK strategy."))

    duplicate_visuals: set[str] = set()
    seen_visuals: set[str] = set()
    long_visuals = 0
    text_heavy = 0
    for index, anchor in enumerate(anchors, start=1):
        visual = str(anchor.get("visual") or "")
        visual_key = re.sub(r"\s+", " ", visual.lower()).strip()
        if visual_key in seen_visuals:
            duplicate_visuals.add(str(index))
        seen_visuals.add(visual_key)

        if len(words(visual)) > 30:
            long_visuals += 1
        if sum(len(segment.split()) for segment in quoted_segments(visual)) > 8:
            text_heavy += 1

        anchor_fact = str(anchor.get("anchor") or "")
        if re.search(r"\b(get it|remember|this is your)\b", anchor_fact, flags=re.I):
            findings.append(Finding("minor", "anchor_contains_mnemonic", f"Anchor {index} fact contains narration/mnemonic wording."))

    if duplicate_visuals:
        findings.append(Finding("major", "duplicate_visuals", f"Duplicate visual descriptions at anchors: {', '.join(sorted(duplicate_visuals))}."))
    if long_visuals:
        findings.append(Finding("minor", "long_visuals", f"{long_visuals} visual descriptions exceed 30 words."))
    if text_heavy:
        findings.append(Finding("major", "text_dependent_visuals", f"{text_heavy} anchors rely on more than 8 quoted label words."))

    if not prompts["prompt1"] or not prompts["prompt2"]:
        findings.append(Finding("critical", "missing_prompts", "Bundle does not include both image prompts."))
    if "Hook:" in prompt2 and "invisible design guidance" not in prompt2:
        findings.append(Finding("major", "hook_may_render", "Prompt includes Hook guidance but does not explicitly forbid rendering it as text."))
    if "Encodes:" in prompt2 and "invisible design guidance" not in prompt2:
        findings.append(Finding("major", "encodes_may_render", "Prompt includes Encodes guidance but does not explicitly forbid rendering it as text."))
    if "spatial hierarchy" not in prompt2.lower() and "uncluttered" not in prompt2.lower():
        findings.append(Finding("minor", "weak_spatial_map", "Prompt does not explicitly preserve spatial hierarchy/uncluttered zones."))
    if re.search(r"\b(?:Sketchy|Pixorize)\b", prompts["prompt1"] + prompts["prompt2"], flags=re.I):
        findings.append(Finding("minor", "brand_style_reference", "Prompt still references commercial mnemonic brands; prefer principle-based style language."))

    score = 100
    for finding in findings:
        score -= {"critical": 30, "major": 12, "minor": 5}.get(finding.severity, 3)
    return max(score, 0), findings


def md_escape(text: Any) -> str:
    return str(text or "").replace("\n", "<br>").replace("|", "\\|")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def build_pack(bundle_path: Path, output_root: Path) -> Path:
    bundle = read_bundle(bundle_path)
    topic = str(bundle.get("topic") or bundle.get("story", {}).get("scene_title") or bundle_path.stem)
    pack_dir = output_root / slugify(topic)
    prompts = image_prompts(bundle)
    anchors = anchor_lines(bundle)
    score, findings = audit_bundle(bundle)
    now = datetime.now(timezone.utc).isoformat()

    write_text(
        pack_dir / "00_README.md",
        f"""# Visual QA Pack: {topic}

Generated: {now}

Source bundle: `{bundle_path}`

Use this pack to test the Gemini web app without using Mnemorized API image tokens. The Gemini app is a qualitative sandbox, not an exact API-equivalent provider test.

Recommended flow:

1. Open `https://gemini.google.com/app`.
2. Enable `Create images`.
3. Paste `01_gemini_prompt_1_scene_foundation.txt`.
4. Paste `02_gemini_prompt_2_all_anchors.txt` in the same chat.
5. Save the generated image in this pack folder.
6. Complete `05_manual_image_audit.md`.

Auto structural score before image review: **{score}/100**.
""",
    )

    write_text(pack_dir / "01_gemini_prompt_1_scene_foundation.txt", prompts["prompt1"])
    write_text(pack_dir / "02_gemini_prompt_2_all_anchors.txt", prompts["prompt2"])

    rows = [
        "| # | Hook | Visual | Encodes |",
        "|---|---|---|---|",
    ]
    for anchor in anchors:
        rows.append(
            f"| {anchor.get('n', '')} | {md_escape(anchor.get('hook', ''))} | {md_escape(anchor.get('visual', ''))} | {md_escape(anchor.get('anchor', ''))} |"
        )
    write_text(
        pack_dir / "03_anchor_table.md",
        f"# Anchor Table\n\nScene: **{bundle.get('story', {}).get('scene_title', '')}**\n\n" + "\n".join(rows),
    )

    finding_lines = [
        "| Severity | Code | Finding |",
        "|---|---|---|",
    ]
    if findings:
        finding_lines.extend(f"| {f.severity} | `{f.code}` | {md_escape(f.message)} |" for f in findings)
    else:
        finding_lines.append("| pass | `none` | No structural prompt issues detected before image review. |")

    write_text(
        pack_dir / "04_auto_structural_audit.md",
        f"""# Auto Structural Audit

Score: **{score}/100**

Publishable threshold: **{PASS_THRESHOLD}/100 before manual image review**

{chr(10).join(finding_lines)}
""",
    )

    write_text(
        pack_dir / "05_manual_image_audit.md",
        """# Manual Image Audit

Image file reviewed:

Overall decision: PASS / REPAIR / REGENERATE

## Scorecard

Give each category 0-10.

| Category | Score | Notes |
|---|---:|---|
| Anchor completeness: all anchors present |  |  |
| Hook fidelity: visual matches the HOOK |  |  |
| Silhouette strength: works without labels |  |  |
| Medical fidelity: no wrong thresholds/facts implied |  |  |
| Spatial map: coherent zones and sequence |  |  |
| Low clutter: readable 16:9 scene |  |  |
| Text safety: labels optional, short, not wrong |  |  |
| Originality: no copied commercial scene/symbol |  |  |
| Reusability: publishable for learners |  |  |

## Anchor-by-anchor Review

| # | Present? | Hook works? | Label needed? | Problem | Fix idea |
|---|---|---|---|---|---|

## Failure Pattern

Summarize repeatable prompt/system issue if present:

## Next Prompt-System Fix

Only write a system fix here if the failure would repeat across topics:
""",
    )

    write_text(
        pack_dir / "06_gemini_app_single_paste_prompt.txt",
        f"""Generate the image using this two-step Mnemorized prompt sequence.

First use this scene foundation prompt:

{prompts["prompt1"]}

Then refine the same image with all anchors using this prompt:

{prompts["prompt2"]}
""",
    )

    (pack_dir / "anchors.json").write_text(json.dumps(anchors, indent=2), encoding="utf-8")
    return pack_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build visual QA packs from exported Mnemorized forge bundles.")
    parser.add_argument("inputs", nargs="+", type=Path, help="Bundle JSON files or directories containing *_bundle.json files.")
    parser.add_argument("--output-root", type=Path, default=Path("local_archive") / "visual_qa_packs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = bundle_paths(args.inputs)
    if not paths:
        raise SystemExit("No *_bundle.json files found.")
    for path in paths:
        pack_dir = build_pack(path, args.output_root)
        print(pack_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
