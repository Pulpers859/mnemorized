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

# CANONICAL RUBRIC — mirror of docs/image-scoring-rubric.md and the in-app
# frontend/scripts/forge-image-audit.js RUBRIC. Keep all three in sync. The image
# score is deterministic: six weighted categories (sum 100) minus per-defect
# deductions, then capped by any triggered hard gate. OVERALL = min(RAW, caps).
CANONICAL_RUBRIC = """SCORING METHOD (deterministic — show the arithmetic):
1. Start each category at its full value; subtract the per-defect deductions.
2. RAW_SUM = sum of the six categories (max 100).
3. Apply every triggered HARD GATE; each gate CAPS OVERALL (it does not subtract).
4. OVERALL_SCORE = min(RAW_SUM, lowest triggered gate cap), rounded to an integer.
When torn between two scores, choose the LOWER.

CATEGORIES (weights sum to 100):
A. Anchor Completeness — 30. -10 per absent/unidentifiable anchor; -5 per anchor too
   tiny/crowded to read; -3 per anchor identifiable ONLY by an attached label.
B. Hook Fidelity — 20. -8 per anchor rendered as TEXT SLAPPED ON A GENERIC PROP
   (barrel/wall/crate/plaque) when a sanctioned metaphor existed (banana=potassium,
   salt shaker=sodium, box of baking soda=bicarbonate, skull=toxicity, hourglass=time,
   turtle=slow, padlock=restricted...); -4 per weak/arbitrary object; -2 per weaker
   tier than warranted. Do NOT penalize a correct functional/contrast hook on a
   threshold DECISION (e.g. traffic-light=K+).
C. Silhouette & Legibility — 15. -5 illegible clutter; -4 duplicated identical
   silhouettes; -3 reading path lost to busyness.
D. Text Discipline — 15. -6 per misspelled/invented required label; -5 meta-
   instruction/caption/zone text leaked into image; -3 per crammed multi-line label
   list; -2 per needless label the metaphor already carried.
E. Medical Fidelity — 10. -10 an implied fact/threshold is WRONG; -4 ambiguous dose.
F. Scene Coherence — 10. -6 segmented grid/booths/panels instead of one scene; -3
   incoherent floating placement. A deliberately off-theme sanctioned metaphor is NOT a
   coherence defect (bizarreness effect is intended).

HARD GATES (cap OVERALL; use the lowest triggered cap):
G1: 1 anchor missing->cap 79; 2->cap 70; 3+->cap 55.
G2: any misspelled/invented required label->cap 88.
G3: meta-instruction/caption/zone text leaked into image->cap 85.
G4: segmented grid/booths/panels instead of one scene->cap 80.
G5: any medically wrong fact/threshold implied->cap 75.
G6: any anchor encoded ONLY as text on a generic prop (no visual hook) when a
    sanctioned metaphor/stronger hook existed->cap 90.

DECISION: PASS = OVERALL>=96 AND no G1/G2/G5. PASS_WITH_TEXT_RISK = OVERALL>=90, no
G1/G5, but G2/G3/G6 present. REPAIR = 70..95 with a bounded fixable defect.
REGENERATE = OVERALL<70 or 2+ anchors missing. Never PASS if any anchor is missing.

ANTI-INFLATION: external auditor only (never self-grade); a label alone never
satisfies an anchor (needs shape/interaction/placement); treat labels as unreliable
unless legible AND correctly spelled; do not invent anchors that are not visible;
numbers/doses/formulas must NOT appear as drawn text at all (exact values live in the
narration/flashcards) — a spelled-out value is a text-discipline defect, not a feature;
on a plate with >8 anchors, re-verify before claiming all present."""

RUBRIC_OUTPUT_FORMAT = """OVERALL_SCORE: <integer 0-100>
DECISION: <PASS | PASS_WITH_TEXT_RISK | REPAIR | REGENERATE>
CATEGORY_SCORES: A:<0-30> B:<0-20> C:<0-15> D:<0-15> E:<0-10> F:<0-10>
RAW_SUM: <integer 0-100>
GATES_TRIGGERED: <e.g. "G1(1 missing) cap79; G6 cap90" or "none">
ANCHORS_PRESENT: <integer>/<total>
MISSING_ANCHORS: <comma-separated anchor numbers, or none>
TOP_ISSUES: <up to 3 short phrases separated by "; ", or none>
REPAIR: <one or two sentences on the single highest-impact fix, or none>"""

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

NO_PRECISION_TEXT_RULE = (
    "NO PRECISION TEXT: do NOT render numbers, digits, doses, units, thresholds, lab values, or formulas as text anywhere in the image "
    "(no plaques, dials, gauges, tags, or chalk marks bearing values). A drawn number is a flashcard, not a mnemonic — the exact value is "
    "spoken in the narration and listed in the flashcards, never printed in the picture. A number may appear ONLY when encoded as a visual "
    "hook (a shape look-alike or a small countable quantity), never as spelled-out digits. If a value cannot be cleanly encoded, omit it from the image."
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

_CONSTITUTION_PATH = Path(__file__).resolve().parents[1] / "docs" / "gemini-constitution.txt"
_ = _CONSTITUTION_PATH.read_text(encoding="utf-8")

COMPACT_GEMINI_GUARDRAILS = (
    "Gemini render checklist: use only coarse spatial terms; no compound positions; "
    "no micro-poses, exact finger positions, clock-hand angles, shaped flames, or surface-contrast tricks. "
    "Use completed-state language. Reserve all-caps only for intended visible labels. "
    "Avoid descriptor nouns such as pharmacy label or warning sign. "
    "Each character holds at most two items. Unique props say one single item if duplication would confuse the cue. "
    "No captions, subtitles, booth titles, numbered panels, grids, checklists, speech bubbles, or black text strips. "
    "Visible text must be physically integrated into objects and limited to essential labels."
)

MICRO_POSE_RE = re.compile(
    r"\b(?:interlocked|laced\s+together|balloon[- ]puffed|comically\s+distended|"
    r"fingers?\s+(?:spread|curled|wrapped|gripping)|"
    r"knee\s+(?:bent|driving|lifted)|"
    r"exact(?:ly)?\s+(?:at|level|height)|"
    r"halfway\s+between|belt[- ]buckle\s+(?:level|height)|"
    r"navel\s+level|mid[- ](?:stride|step|crouch))\b",
    re.I,
)

COMPOUND_POSITION_RE = re.compile(
    r"\b(?:center[- ]left|center[- ]right|foreground[- ](?:left|right)|"
    r"background[- ](?:left|right))\b",
    re.I,
)

ZONE_CYCLE = [
    "LEFT",
    "LEFT",
    "CENTER",
    "CENTER",
    "CENTER",
    "RIGHT",
    "RIGHT",
    "FOREGROUND",
    "FOREGROUND",
    "FOREGROUND",
    "BACKGROUND",
    "BACKGROUND",
    "BACKGROUND",
    "BACKGROUND",
    "FOREGROUND",
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


TEXT_SURFACE_RE = re.compile(
    r"\b(?:label(?:ed)?|marked|stamped|reads?|says?|text|printed|engraved|writing|word(?:s)?)\b",
    re.I,
)
VISUAL_META_RE = re.compile(
    r"\b(?:no\s+(?:extra\s+)?text\s+labels?|no\s+(?:extra\s+)?labels?|single\s+text\s+element|two\s+text\s+elements?|text\s+elements?)\b",
    re.I,
)


def visible_text_surface_count(text: str) -> int:
    """Estimate how many visible text-bearing surfaces an anchor asks for."""
    if not text:
        return 0
    text = VISUAL_META_RE.sub("", text)
    quoted = len(quoted_segments(text))
    explicit = len(TEXT_SURFACE_RE.findall(text))
    semicolon_pressure = 1 if ";" in text and explicit else 0
    return max(quoted, explicit) + semicolon_pressure


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


COMPOUND_TO_COARSE = [
    (re.compile(r"\bcenter[- ]left\b", re.I), "left"),
    (re.compile(r"\bcenter[- ]right\b", re.I), "right"),
    (re.compile(r"\bforeground[- ]left\b", re.I), "foreground"),
    (re.compile(r"\bforeground[- ]right\b", re.I), "foreground"),
    (re.compile(r"\bbackground[- ]left\b", re.I), "background"),
    (re.compile(r"\bbackground[- ]right\b", re.I), "background"),
    (re.compile(r"\bfar\s+background\s+left\b", re.I), "background"),
    (re.compile(r"\bfar\s+background\s+right\b", re.I), "background"),
    (re.compile(r"\bfar\s+left\b", re.I), "left"),
    (re.compile(r"\bfar\s+right\b", re.I), "right"),
]


def condense_for_image(visual: str) -> str:
    text = (visual or "").replace("↑", "").replace("↓", "")

    for pattern, replacement in COMPOUND_TO_COARSE:
        text = pattern.sub(replacement, text)

    text = MICRO_POSE_RE.sub("", text)
    text = VISUAL_META_RE.sub("", text)
    text = re.sub(r"\bno\s+text\b", "", text, flags=re.I)
    text = re.sub(r"\s{2,}", " ", text).strip()

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
        anchor_lines_text.append(
            f"- {str(anchor.get('zone')).lower()}: {condense_for_image(str(anchor.get('visual') or ''))}."
        )

    n = len(anchors)
    prompt1 = f"{ROOM_STYLE}\n\n{scene_desc}"
    prompt2 = (
        f"{VISUAL_STYLE}\n\n{scene_desc}\n\n"
        f"{ANTI_META_TEXT}\n\n"
        "SCENE OBJECT RULE: Do NOT label or name any part of the room itself (walls, floor, ceiling, beams, furniture). "
        "Background surfaces are unlabeled.\n\n"
        f"Add ALL {n} of the following medical mnemonic objects to the scene. "
        "They may be props, characters/figures, or interactive elements — visual mnemonics, not labeled infographics. "
        "Preserve clear spatial hierarchy: left/center/right/foreground/background zones must stay readable and uncluttered. "
        "Each anchor should be recognizable by its SHAPE and SILHOUETTE first. "
        f"{ANCHOR_LEGIBILITY_RULE} "
        "Text labels are secondary and optional — if present, maximum 3 words per ordinary label. "
        f"{NO_PRECISION_TEXT_RULE} "
        f"{EXACT_LABEL_RULE} "
        f"{COMPACT_GEMINI_GUARDRAILS} "
        "SCENE TEXT BUDGET: at most 12 short mnemonic name labels in the ENTIRE image, and ZERO numeric/dose/threshold/formula text. "
        "Character names count. "
        "Zone words below guide placement only — do NOT render zone text or bullet text:\n\n"
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
    too_many_text_surfaces = 0
    visual_meta_leaks = 0
    micro_pose_anchors = 0
    compound_position_anchors = 0
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
        if visible_text_surface_count(visual) > 2:
            too_many_text_surfaces += 1
        if VISUAL_META_RE.search(visual):
            visual_meta_leaks += 1
        if MICRO_POSE_RE.search(visual):
            micro_pose_anchors += 1
        if COMPOUND_POSITION_RE.search(visual):
            compound_position_anchors += 1

        anchor_fact = str(anchor.get("anchor") or "")
        if re.search(r"\b(get it|remember|this is your)\b", anchor_fact, flags=re.I):
            findings.append(Finding("minor", "anchor_contains_mnemonic", f"Anchor {index} fact contains narration/mnemonic wording."))

    if duplicate_visuals:
        findings.append(Finding("major", "duplicate_visuals", f"Duplicate visual descriptions at anchors: {', '.join(sorted(duplicate_visuals))}."))
    if long_visuals:
        findings.append(Finding("minor", "long_visuals", f"{long_visuals} visual descriptions exceed 30 words."))
    if text_heavy:
        findings.append(Finding("major", "text_dependent_visuals", f"{text_heavy} anchors rely on more than 8 quoted label words."))
    if too_many_text_surfaces:
        findings.append(Finding("major", "too_many_text_surfaces", f"{too_many_text_surfaces} anchors request more than two visible text-bearing surfaces."))
    if visual_meta_leaks:
        findings.append(Finding("major", "visual_meta_leak", f"{visual_meta_leaks} visual descriptions include meta-instructions instead of drawable scene content."))
    if micro_pose_anchors:
        findings.append(Finding("major", "micro_poses", f"{micro_pose_anchors} anchors contain micro-pose descriptions that Gemini cannot render (exact finger/hand/face positions)."))
    if compound_position_anchors:
        findings.append(Finding("minor", "compound_positions", f"{compound_position_anchors} anchors use compound spatial positions (e.g., center-left) instead of single-axis terms."))

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
        f"""# Manual Image Audit

Image file reviewed:

Scored with the CANONICAL RUBRIC (docs/image-scoring-rubric.md). Fill the six
category scores, subtract per-defect deductions, sum to RAW, then apply the lowest
triggered gate cap. OVERALL = min(RAW, cap).

## Scorecard (weights sum to 100)

| Category (max) | Score | Deductions applied |
|---|---:|---|
| A. Anchor completeness (30) |  |  |
| B. Hook fidelity (20) |  |  |
| C. Silhouette & legibility (15) |  |  |
| D. Text discipline (15) |  |  |
| E. Medical fidelity (10) |  |  |
| F. Scene coherence (10) |  |  |
| **RAW_SUM (100)** |  |  |

Gates triggered (G1 1miss=cap79/2=70/3+=55; G2 misspelled=88; G3 text-leak=85;
G4 grid=80; G5 wrong-fact=75; G6 text-on-prop hook=90):

**OVERALL = min(RAW_SUM, lowest cap): ____   DECISION: PASS / PASS_WITH_TEXT_RISK / REPAIR / REGENERATE**

(PASS only if OVERALL>=96 and no G1/G2/G5. Never PASS with any anchor missing.)

## Anchor-by-anchor Review

| # | Present? | Hook works (not text-on-prop)? | Label needed? | Problem | Fix idea |
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
        f"""You are the external auditor for a generated Mnemorized medical visual mnemonic image.

I will provide the generated image plus the anchor table below. Compare the image against the anchor table using the CANONICAL RUBRIC. Do not praise the image; grade it.

This rubric is authoritative — it is the same standard used by the in-app Image
Quality Gate and documented in docs/image-scoring-rubric.md. Score by the arithmetic,
not by impression.

{CANONICAL_RUBRIC}

Return the required scoreblock EXACTLY (no markdown), with OVERALL_SCORE = min(RAW_SUM, lowest gate cap):

{RUBRIC_OUTPUT_FORMAT}

Then, below the scoreblock, add these supporting sections:

ANCHOR_AUDIT:
| # | Present? | Hook fidelity | Silhouette/readability | Text/label accuracy | Medical risk | Fix |
|---|---|---|---|---|---|---|

SYSTEMIC_FAILURES:
- [List repeatable prompt-contract failures only. If none, write "None."]

REPAIR_PROMPT:
[If DECISION is REPAIR, write a concise image-edit prompt that fixes only the failed items while preserving the good composition. Otherwise write "N/A".]

REGENERATION_PROMPT_CHANGE:
[If DECISION is REGENERATE or there is a systemic prompt issue, write the prompt-contract change needed before regenerating. Otherwise write "N/A".]

ANCHOR TABLE:

{plain_table}
""",
    )

    write_text(
        pack_dir / "08_repair_or_regenerate_prompt_template.txt",
        f"""Use this after completing `07_gemini_image_audit_prompt.txt`.

## REPAIR LOOP RULES (mandatory)

1. The repaired prompt must be SHORTER than or equal to the original. Longer repairs score worse.
2. NEVER add micro-poses (exact finger positions, facial muscle states, joint angles). If an audit says "hands are wrong," REMOVE the hand description entirely.
3. NEVER add ground/surface contrast details (pristine here vs scorched there). If floor detail failed, drop it. Let contrast live in objects/figures, not background surfaces.
4. Rewrite the ENTIRE director prompt from scratch using different visual strategies. Do not patch individual sentences or append audit feedback.
5. Use ONLY coarse spatial terms: LEFT, CENTER, RIGHT, FOREGROUND, BACKGROUND. Never use compound positions (center-left, foreground-right).
6. Maximum 5 repair iterations per plate. If still failing after 5 attempts, redesign the anchor's visual hook — the encoding strategy is wrong, not just the wording.

## If REPAIR

Rewrite the full director prompt for this plate/scene. Keep the same mnemonic hook and required labels but use SIMPLER visual encoding. The new prompt must be shorter than the previous version.

Do NOT paste this into Gemini:
- Audit feedback text
- "Fix the hands" / "move the figure" patch instructions
- Any sentence containing micro-pose language

Instead, write a clean standalone prompt that a fresh Gemini session can render without context from previous attempts.

## If REGENERATE

Rebuild the prompt from scratch. Checklist:

- Are all anchors present with hooks and visual cues?
- Are precision numbers/formulas preserved exactly?
- Are labels short (1-4 words) and exact?
- Are anchors large enough at 1024px width?
- Does EVERY spatial term use single-axis coarse positions only?
- Does the prompt contain ZERO micro-pose descriptions?
- Is the total word count under 250 (single plate) or 600 (full scene)?
- Does the prompt avoid commercial visual mnemonic names?

Then regenerate from a fresh Gemini chat.

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
