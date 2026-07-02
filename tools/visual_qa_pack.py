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

VISUAL_STYLE = (
    "Hand-drawn 2D cartoon illustration drawn with Micron pens and Copic markers on paper then scanned. "
    "Wobbly, imperfect ink outlines with visible line weight variation. NO clean digital vector lines. "
    "Cell-shaded flat coloring with one base color and one hard-edged shadow color per surface. "
    "Rich saturated Copic marker palette with strong contrast. "
    "Angular editorial-cartoon caricatures with distinctive silhouettes, not anime, not 3D, not realistic. "
    "Hand-drawn educational visual mnemonic poster, dense but readable medical teaching map. "
    "No gradients, no atmospheric haze, no depth of field blur, no glowing effects."
)

ROOM_STYLE = (
    "Hand-drawn 2D cartoon illustration drawn with Micron pens and Copic markers on paper then scanned. "
    "Wobbly, imperfect ink outlines with flat marker coloring. "
    "Hand-drawn educational visual mnemonic background, dense but readable medical teaching map. "
    "EMPTY ROOM ONLY — absolutely NO people, NO characters, NO figures, NO animals. "
    "NO text, NO labels, NO signs, NO writing on any surface. Just the bare room."
)

ANTI_META_TEXT = (
    "TEXT RULES: Do NOT render any floating labels, zone names, category descriptions, or meta-commentary as visible text. "
    "The ONLY text that should appear is text that is physically part of an object in the scene. "
    "No floating captions. No zone labels. No anchor descriptions."
)

PRECISION_TEXT_RULE = (
    "PRECISION TEXT EXCEPTION: short numbers, thresholds, units, and compact formulas are allowed when they are the tested fact. "
    "They must be physically attached to the mnemonic object as a plaque, dial, ruler mark, scale beam, gauge face, or chalk mark. "
    "Do not use text as the whole mnemonic: every precision label must sit on a strong non-text visual device that still reads by silhouette. "
    "Keep precision text large, sparse, accurate, and readable; no sentences or paragraph labels."
)

ANCHOR_LEGIBILITY_RULE = (
    "ANCHOR LEGIBILITY RULE: every anchor must be large enough to identify at normal 1024px image size. "
    "No anchor may become tiny shelf clutter. Give each anchor clear empty space, a distinct silhouette, and enough scale to read its key shape before reading any label. "
    "If a shelf or wall contains multiple anchors, stagger them vertically and enlarge each one instead of lining up small similar props."
)

EXACT_LABEL_RULE = (
    "EXACT LABEL RULE: if a visual specifies a short label, copy it exactly. "
    "Do not invent alternate spellings, abbreviations, or nonsense words. Sound-alike character names must appear exactly when the name carries the mnemonic. "
    "If exact text would be too small or uncertain, replace it with a larger physical symbol instead of misspelling it."
)

ZONE_CYCLE = [
    "FAR LEFT",
    "LEFT",
    "CENTER LEFT",
    "CENTER",
    "CENTER RIGHT",
    "RIGHT",
    "FAR RIGHT",
    "FOREGROUND LEFT",
    "FOREGROUND CENTER",
    "FOREGROUND RIGHT",
    "BACKGROUND LEFT",
    "BACKGROUND CENTER",
    "BACKGROUND RIGHT",
    "BACKGROUND CORNER",
    "DOORWAY",
]

ZONE_KEYWORDS = [
    (re.compile(r"\b(?:far\s+)?left\s+wall\b", re.I), "LEFT WALL"),
    (re.compile(r"\b(?:far\s+)?right\s+wall\b", re.I), "RIGHT WALL"),
    (re.compile(r"\bback\s+(?:corner|wall)\b", re.I), "BACKGROUND CORNER"),
    (re.compile(r"\bforeground\b", re.I), "FOREGROUND CENTER"),
    (re.compile(r"\bcenter\b", re.I), "CENTER"),
    (re.compile(r"\bceiling\b", re.I), "ABOVE CENTER"),
    (re.compile(r"\bfloor\b|on\s+the\s+ground\b", re.I), "FOREGROUND CENTER"),
    (re.compile(r"\bleft\b", re.I), "LEFT"),
    (re.compile(r"\bright\b", re.I), "RIGHT"),
]


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


def scene_description_from_prompt1(prompt1: str) -> str:
    if "\n\n" in prompt1:
        return prompt1.split("\n\n", 1)[1].strip()
    return prompt1.strip() or "Wide uncluttered memory-palace room with clear left, center, right, foreground, and background zones, aspect ratio 16:9"


def extract_zone(visual: str, fallback: str) -> str:
    for pattern, zone in ZONE_KEYWORDS:
        if pattern.search(visual):
            return zone
    return fallback


def condense_for_image(visual: str) -> str:
    text = (visual or "").replace("↑", "").replace("↓", "")

    def replace_quote(match: re.Match[str]) -> str:
        prefix = match.group(1)
        inner = match.group(2)
        if re.search(r"[=×+\-±<>≤≥÷/]|\d", inner) and len(inner) <= 70:
            return f'{prefix}"{inner}"'
        parts = [part.strip() for part in re.split(r"[/,;]+", inner) if part.strip()]
        if len(parts) > 2:
            return prefix + '"' + " / ".join(parts[:2]) + ' …"'
        return prefix + '"' + inner[:24] + '…"'

    return re.sub(r'(^|[\s(:])"([^"]{25,})"', replace_quote, text)


def refreshed_prompts(bundle: dict[str, Any]) -> dict[str, str]:
    prompts = image_prompts(bundle)
    scene_desc = scene_description_from_prompt1(prompts["prompt1"])
    anchors = anchor_lines(bundle)
    assigned = []
    for index, anchor in enumerate(anchors):
        visual = str(anchor.get("visual") or "")
        assigned.append({**anchor, "zone": extract_zone(visual, ZONE_CYCLE[index % len(ZONE_CYCLE)])})
    anchor_lines_text = []
    for anchor in assigned:
        hook = f" Hook: {anchor.get('hook')}." if anchor.get("hook") else ""
        encodes = f" Encodes: {anchor.get('anchor')}" if anchor.get("anchor") else ""
        anchor_lines_text.append(
            f"  ({str(anchor.get('zone')).lower()}) Anchor {anchor.get('n', '')}:{hook} "
            f"Visual: {condense_for_image(str(anchor.get('visual') or ''))}.{encodes}"
        )

    n = len(anchors)
    prompt1 = f"{ROOM_STYLE}\n\n{scene_desc}"
    prompt2 = (
        f"{VISUAL_STYLE}\n\n{scene_desc}\n\n"
        f"{ANTI_META_TEXT}\n\n"
        "SCENE OBJECT RULE: Do NOT label or name any part of the room itself (walls, floor, ceiling, beams, furniture). "
        "Background surfaces are unlabeled.\n\n"
        f"Add ALL {n} of the following medical mnemonic anchors to the scene. "
        "Anchors may be objects, characters/figures, or interactive elements — they are VISUAL MNEMONICS, not labeled props. "
        'The words "Hook" and "Encodes" are invisible design guidance only — do NOT render them as text. '
        "Preserve clear spatial hierarchy: left/center/right/foreground/background zones must stay readable and uncluttered. "
        "Each anchor should be recognizable by its SHAPE and SILHOUETTE first. "
        f"{ANCHOR_LEGIBILITY_RULE} "
        "Text labels are secondary and optional — if present, maximum 3 words per ordinary label. "
        f"{PRECISION_TEXT_RULE} "
        f"{EXACT_LABEL_RULE} "
        "SCENE TEXT BUDGET: maximum 12 ordinary text labels plus up to 4 precision labels for numbers/formulas in the ENTIRE image. "
        "Character names and short numbers count. "
        "Zone hints in parentheses guide placement — do NOT render zone text:\n\n"
        + "\n".join(anchor_lines_text)
        + f"\n\nAll {n} anchors must be present and visually distinct. "
        "Do NOT add labels to room surfaces, walls, beams, or background objects. "
        "Maintain same lighting, color palette, and atmosphere."
    )
    return {"prompt1": prompt1, "prompt2": prompt2}


def audit_bundle(bundle: dict[str, Any], prompts_override: dict[str, str] | None = None) -> tuple[int, list[Finding]]:
    findings: list[Finding] = []
    anchors = anchor_lines(bundle)
    prompts = prompts_override or image_prompts(bundle)
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


def plain_anchor_table(anchors: list[dict[str, Any]]) -> str:
    lines = ["# Anchor Table", ""]
    for anchor in anchors:
        lines.append(f"Anchor {anchor.get('n', '')}")
        lines.append(f"HOOK: {anchor.get('hook', '')}")
        lines.append(f"VISUAL: {anchor.get('visual', '')}")
        lines.append(f"ENCODES: {anchor.get('anchor', '')}")
        lines.append("")
    return "\n".join(lines).strip()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def build_pack(bundle_path: Path, output_root: Path, refresh_prompt_contract: bool = False) -> Path:
    bundle = read_bundle(bundle_path)
    topic = str(bundle.get("topic") or bundle.get("story", {}).get("scene_title") or bundle_path.stem)
    pack_dir = output_root / slugify(topic)
    prompts = refreshed_prompts(bundle) if refresh_prompt_contract else image_prompts(bundle)
    anchors = anchor_lines(bundle)
    score, findings = audit_bundle(bundle, prompts_override=prompts)
    now = datetime.now(timezone.utc).isoformat()
    contract_note = "Prompt files were rebuilt from the saved story using the current visual QA prompt contract." if refresh_prompt_contract else "Prompt files are copied from the exported bundle."

    write_text(
        pack_dir / "00_README.md",
        f"""# Visual QA Pack: {topic}

Generated: {now}

Source bundle: `{bundle_path}`

Use this pack to test the Gemini web app without using Mnemorized API image tokens. The Gemini app is a qualitative sandbox, not an exact API-equivalent provider test.

{contract_note}

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
    plain_table = plain_anchor_table(anchors)
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

    write_text(
        pack_dir / "07_gemini_image_audit_prompt.txt",
        f"""You are auditing a generated Mnemorized medical visual mnemonic image.

I will provide the generated image plus the anchor table below. Your job is to compare the image against the anchor table, not to praise the image.

Audit rules:
- Do not invent anchors that are not visible.
- Treat labels as unreliable unless they are readable and spelled correctly.
- A label alone is not enough; the visual must also have a recognizable shape, character, object interaction, or spatial placement.
- Numeric thresholds and compact formulas are allowed, but they must be attached to a visible mnemonic device.
- Score harshly. If an anchor is too tiny, crowded, misspelled, missing, medically ambiguous, or only text-dependent, mark it as a problem.
- Do not suggest copying any proprietary visual mnemonic product.

Return exactly this structure:

OVERALL_SCORE: [0-100]
DECISION: PASS / REPAIR / REGENERATE

SUMMARY:
[2-4 blunt sentences]

ANCHOR_AUDIT:
| # | Present? | Hook fidelity | Silhouette/readability | Text/label accuracy | Medical risk | Fix |
|---|---|---|---|---|---|---|

SYSTEMIC_FAILURES:
- [List repeatable prompt-contract failures only. If none, write "None."]

REPAIR_PROMPT:
[If DECISION is REPAIR, write a concise image-edit prompt that fixes only the failed items while preserving the good composition. If DECISION is REGENERATE, write "N/A". If DECISION is PASS, write "N/A".]

REGENERATION_PROMPT_CHANGE:
[If DECISION is REGENERATE or there is a systemic prompt issue, write the prompt-contract change needed before regenerating. Otherwise write "N/A".]

ANCHOR TABLE:

{plain_table}
""",
    )

    write_text(
        pack_dir / "08_repair_or_regenerate_prompt_template.txt",
        f"""Use this after completing `07_gemini_image_audit_prompt.txt`.

If the audit decision is REPAIR, paste the generated image and this prompt into Gemini after replacing the bracketed sections:

Edit the image you just generated. Keep the same composition, room, characters, colors, and hand-drawn style. Make ONLY these corrections:

[Paste the failed anchor fixes from the audit here.]

Preserve all correct anchors, formulas, labels, and spatial positions. Do not add new captions, zone labels, explanatory text, or extra anchors. This is a precision repair, not a redesign.

If the audit decision is REGENERATE, rebuild the prompt first. Use this checklist:

- Are all 8-10 anchors present in the prompt?
- Does every anchor include a hook and visual cue?
- Are precision numbers/formulas preserved exactly?
- Are labels short and exact?
- Are anchors large enough at 1024px width?
- Are shelf/wall anchors staggered instead of tiny clutter?
- Does the prompt avoid commercial visual mnemonic names and copied motifs?

Then regenerate from `02_gemini_prompt_2_all_anchors.txt` or from a refreshed pack created with `--refresh-prompt-contract`.

Topic: {topic}
""",
    )

    (pack_dir / "anchors.json").write_text(json.dumps(anchors, indent=2), encoding="utf-8")
    return pack_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build visual QA packs from exported Mnemorized forge bundles.")
    parser.add_argument("inputs", nargs="+", type=Path, help="Bundle JSON files or directories containing *_bundle.json files.")
    parser.add_argument("--output-root", type=Path, default=Path("local_archive") / "visual_qa_packs")
    parser.add_argument(
        "--refresh-prompt-contract",
        action="store_true",
        help="Rebuild prompt files from saved story anchors using the current QA prompt contract.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = bundle_paths(args.inputs)
    if not paths:
        raise SystemExit("No *_bundle.json files found.")
    for path in paths:
        pack_dir = build_pack(path, args.output_root, refresh_prompt_contract=args.refresh_prompt_contract)
        print(pack_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
