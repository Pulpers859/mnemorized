#!/usr/bin/env python3
"""Run an end-to-end visual mnemonic stress loop against provider APIs.

This local tool is intentionally outside the app runtime. It uses ignored
developer credentials from backend/.env, writes artifacts to an ignored
troubleshooting directory, and gives future agents a repeatable way to test:

topic -> story anchors -> image prompts -> Gemini image -> image audit -> repair
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import time
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.visual_qa_pack import build_pack, refreshed_prompts


ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
DEFAULT_GEMINI_AUDIT_MODEL = "gemini-2.5-flash"
TARGET_SCORE = 96

# CANONICAL RUBRIC — mirror of docs/image-scoring-rubric.md, the in-app
# frontend/scripts/forge-image-audit.js RUBRIC, and tools/visual_qa_pack.py. Keep
# all in sync. Image score is deterministic: six weighted categories (sum 100) minus
# per-defect deductions, then capped by any triggered hard gate. OVERALL=min(RAW,caps).
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

# Gate caps for deterministic recomputation of OVERALL from the auditor's own fields.
_GATE_CAPS = {"G2": 88, "G3": 85, "G4": 80, "G5": 75, "G6": 90}


def _g1_cap(missing_count: int) -> int:
    if missing_count >= 3:
        return 55
    if missing_count == 2:
        return 70
    if missing_count == 1:
        return 79
    return 100


@dataclass
class TopicCase:
    slug: str
    title: str
    prompt: str


DEFAULT_TOPICS = [
    TopicCase(
        slug="sepsis_septic_shock_initial_management",
        title="Sepsis and septic shock initial management",
        prompt=(
            "Sepsis and septic shock initial management for medical students. Include Sepsis-3 definition, "
            "qSOFA/SOFA risk recognition, lactate, blood cultures before antibiotics when feasible, "
            "broad-spectrum antibiotics within 1 hour for shock/high likelihood sepsis, 30 mL/kg crystalloid "
            "for hypotension or lactate >=4, norepinephrine first-line vasopressor to MAP >=65, source control, "
            "reassessment of perfusion, repeat lactate if elevated, and steroid role for refractory shock. "
            "Preserve exact thresholds and timing."
        ),
    ),
    TopicCase(
        slug="acute_coronary_syndrome_stemi_management",
        title="Acute coronary syndrome / STEMI initial management",
        prompt=(
            "Acute coronary syndrome and STEMI initial ED management for medical students. Include immediate ECG "
            "within 10 minutes, STEMI criteria, aspirin loading, P2Y12/heparin basics, nitrates contraindications "
            "including PDE5 inhibitors and RV infarct/hypotension, oxygen only if hypoxemic, high-intensity statin, "
            "PCI door-to-balloon <=90 minutes, fibrinolysis if PCI unavailable within appropriate window, troponin "
            "trend for NSTEMI, and dangerous mimics like aortic dissection. Preserve exact thresholds and timing."
        ),
    ),
    TopicCase(
        slug="toxic_alcohol_poisoning_diagnosis_treatment",
        title="Toxic alcohol poisoning diagnosis and treatment",
        prompt=(
            "Toxic alcohol poisoning diagnosis and treatment for medical students. Include methanol vs ethylene glycol, "
            "early osmolar gap then later anion gap metabolic acidosis, visual symptoms for methanol, calcium oxalate "
            "crystals/renal injury for ethylene glycol, fomepizole mechanism blocking alcohol dehydrogenase, ethanol "
            "alternative, indications for hemodialysis including severe acidosis/end-organ toxicity/high levels, folinic "
            "acid for methanol, thiamine/pyridoxine for ethylene glycol, and do not wait for confirmatory levels when "
            "suspicion is high. Preserve formulas and thresholds if included."
        ),
    ),
]


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()[:80] or "topic"


def strip_code_fences(text: str) -> str:
    return re.sub(r"^```(?:xml|json)?\s*|\s*```$", "", text.strip(), flags=re.I | re.S).strip()


def tag_text(text: str, tag: str) -> str:
    match = re.search(fr"<{tag}>(.*?)</{tag}>", text, flags=re.I | re.S)
    return match.group(1).strip() if match else ""


def parse_story_xml(text: str) -> dict[str, Any]:
    cleaned = strip_code_fences(text)
    vo_lines: list[dict[str, Any]] = []
    for index, block in enumerate(re.findall(r"<vo_line>(.*?)</vo_line>", cleaned, flags=re.I | re.S), start=1):
        fields: dict[str, str] = {}
        for name in ("HOOK", "NARRATION", "VISUAL", "ANCHOR"):
            match = re.search(
                fr"{name}\s*:\s*(.*?)(?=\n(?:HOOK|NARRATION|VISUAL|ANCHOR)\s*:|\Z)",
                block.strip(),
                flags=re.I | re.S,
            )
            fields[name.lower()] = re.sub(r"\s+", " ", match.group(1)).strip() if match else ""
        vo_lines.append(
            {
                "n": index,
                "hook": fields["hook"],
                "narration": fields["narration"],
                "visual": fields["visual"],
                "anchor": fields["anchor"],
            }
        )
    return {
        "scene_title": tag_text(cleaned, "scene_title"),
        "opening": tag_text(cleaned, "opening"),
        "voLines": vo_lines,
        "review_script": tag_text(cleaned, "review_script"),
    }


def story_system_prompt() -> str:
    return """You create original medical visual mnemonic memory-palace scripts.

Your output must be suitable for Gemini image generation and must follow this contract:
- Produce exactly 8 anchors when possible. Use 9-10 only if the topic truly cannot be covered by grouped anchors.
- Each anchor must include HOOK, NARRATION, VISUAL, and ANCHOR.
- HOOK explains the encoding strategy: sound-alike, look-alike, functional, contrast, or spatial.
- VISUAL is maximum 30 words and must be silhouette-first: shape, identity, action, scale, and position carry the memory before labels.
- Text labels are allowed only for short names, formulas, cutoffs, thresholds, and timing. Labels must be exact and attached to a visual object.
- Aim for no more than two visible text elements per anchor. A visible text element is any label, number/formula plaque, tag, banner, stamp, dial, gauge, sign, or written word.
- Do not cram a list of labels into one visual. If an anchor needs several facts, encode most with shape/scale/position/action and reserve text only for the essential number or short mnemonic name.
- If the VISUAL starts turning into a label list, simplify it into one stronger object interaction.
- VISUAL must describe only what should be drawn. Do not include meta commentary such as "no text labels", "single text element", or "two text elements".
- LARGE NUMBER RULE: do not encode numbers greater than 12 by asking for exact repeated object counts. Use one strong object with an exact plaque, gauge, dial, ruler, or stamped marker instead.
- HOOK/VISUAL CONSISTENCY RULE: do not claim an anchor is label-free if the tested fact requires a number or formula label.
- Avoid clipboards, checklists, generic posters, ordinary bottles, and repeated same-shaped containers unless they are made visually unique.
- Use original scenes and symbols. Do not copy proprietary visual mnemonic products.
- Group related subitems when necessary, but preserve distinct numbers and thresholds.
- Never output more than 10 <vo_line> blocks. If you find an 11th fact, merge it into the closest existing anchor before responding.
- ANCHOR is the clinical fact only, under 35 words.

Respond using ONLY these XML tags in order:
Do not include <thinking>, markdown, analysis, planning notes, headings, or commentary outside the XML tags.
<scene_title>...</scene_title>
<opening>...</opening>
Then 8 <vo_line> blocks preferred, 9-10 maximum:
<vo_line>
HOOK: ...
NARRATION: ...
VISUAL: ...
ANCHOR: ...
</vo_line>
<review_script>...</review_script>
"""


def story_user_prompt(topic: TopicCase) -> str:
    return f"""Create an original visual mnemonic memory palace narration script for:
{topic.prompt}

Tone: precise, memorable, premium medical education.
Absurdity: 7/10.
Prefer a phonetic scene title when natural. Use a single coherent static room with clear left/center/right/foreground/background zones.
Every anchor must be a masterful visual cue for what the student is trying to remember, not a labeled prop."""


_CONSTITUTION_PATH = REPO_ROOT / "docs" / "gemini-constitution.txt"
GEMINI_CAPABILITY_RULES = _CONSTITUTION_PATH.read_text(encoding="utf-8").strip()


def visual_director_system_prompt() -> str:
    return f"""You are the visual director for Mnemorized medical mnemonic images.

Your job is to rewrite a generated anchor table into ONE coherent Gemini image prompt.
Optimize for image adherence, not for prose completeness.

Principles:
- Scene first: make one memorable room with a clear visual metaphor and reading path ("the eye enters at X, sweeps through Y, climbs to Z").
- Open with style and format: "Detailed hand-drawn medical mnemonic illustration in warm ink-and-watercolor style, wide 16:9 format, every element large and silhouette-readable."
- Keep the prompt drawable. Avoid legalistic checklists and long paragraphs.
- Preserve every anchor, but rewrite each as a compact visual beat.
- Compress 8-10 anchors into 6-8 large spatial beats when related facts belong together.
- Put exact numbers/formulas on large physical devices only: gauges, plaques, dials, rulers, scales, clocks, tags.
- For a required NAME label, use the label readability formula: "a large brass plaque bolted to [object] reads [NAME] in bold block letters." Never use vague "stamped with" or bare "reads."
- Avoid ordinary word labels whenever an object/action can carry the meaning. Do not label obvious objects like syringes, vials, kidneys, eyes, pipes, antibiotics, or blood cultures.
- NO PRECISION TEXT: never render numbers, doses, units, thresholds, or formulas as text (no "22", "30 mL/kg", "MAP 65", "1 HR"). Those exact values live in the narration/flashcards; the image carries a hook for the concept. Visible text is limited to short sound-alike NAMES only.
- Always end the prompt with a text allowlist fence: "Visible text limited to these short names: [list]. Render no numbers, doses, units, thresholds, or formulas as text. No other text, no floating captions, no zone labels, no speech bubbles, no directional words anywhere in the image."
- Never ask Gemini to render long medical words unless the exact word is the tested fact.
- Do not encode large numbers as exact object counts above 12.
- Every beat must be large, distinct, and silhouette-readable at 1024px.
- Do not reuse the same base object for two anchors in conflicting states. If one fact is "before" and another is "within 1 hour," use different symbols or a single clear sequence path, not two versions of the same cannon/syringe/clock.
- For multi-criterion clinical screens, use body-icon cues first (brain/fog, heaving ribs, collapsing cuff) and only tiny numeric plaques if essential.
- Use completed-state language for sequences: "has crossed the line" not "crossing," "has swung open" not "opening." Gemini defaults to active states.
- When a feature requires an exact count (e.g., three-headed dog), add explicit verification: "All three heads are clearly visible and separated."
- Write ALL scene directions and emphasis in lowercase. Reserve ALL-CAPS exclusively for labels that must appear as text in the final image.
- Before writing the final prompt, silently check that every source anchor is covered.
- Avoid saying Hook, Encodes, Anchor, station, checklist, rubric, or meta-instructions in the image prompt.
- Final prompt must read like a camera-directed illustration brief, not a numbered list.

{GEMINI_CAPABILITY_RULES}

Return ONLY:
<image_prompt>...</image_prompt>
"""


def visual_director_user_prompt(
    topic: TopicCase,
    story: dict[str, Any],
    room_description: str,
    plate_label: str | None = None,
) -> str:
    anchors = anchor_table(story)
    plate_context = f"\nPLATE: {plate_label}" if plate_label else ""
    return f"""Build a Gemini image prompt for this Mnemorized scene.

TOPIC: {topic.title}
SCENE TITLE: {story.get("scene_title", "")}
EMPTY ROOM FOUNDATION: {room_description}
{plate_context}

ANCHOR TABLE:
{anchors}

Write one image prompt with this structure:
First sentence: style, camera, 16:9, dense but readable hand-drawn medical mnemonic map.
Second sentence: the room metaphor and reading path.
Then one spatial paragraph: "In the left foreground...", "along the left wall...", "at center...", "behind center...", "on the right side...", "in the foreground...", "in the back corner..."
Final sentence: only sparse in-world text for exact numbers, formulas, or mnemonic names; no labels on obvious objects; no floating captions, no zone labels, no checklist or infographic layout.

Do not use a numbered list. Do not use headings. Do not mention anchors, hooks, encodes, stations, or audit language.
Keep the whole image prompt under 1600 words. Make it vivid and draw-focused. Avoid medical explanation except exact labels that must appear."""


def story_subset(story: dict[str, Any], anchors: list[dict[str, Any]], title_suffix: str) -> dict[str, Any]:
    return {
        "scene_title": f"{story.get('scene_title', '')} — {title_suffix}",
        "opening": story.get("opening", ""),
        "voLines": anchors,
        "review_script": "",
    }


def split_anchor_plates(story: dict[str, Any], plate_size: int = 3) -> list[dict[str, Any]]:
    anchors = list(story.get("voLines") or [])
    return [
        story_subset(story, anchors[index:index + plate_size], f"Plate {plate_index}")
        for plate_index, index in enumerate(range(0, len(anchors), plate_size), start=1)
    ]


def room_user_prompt(topic: TopicCase, story: dict[str, Any]) -> str:
    return f"""Write a scene description for a memory palace illustration. Output ONLY the empty room/space, no objects and no style directives.

MEDICAL TOPIC: {topic.title}
SCENE TITLE: {story.get("scene_title", "")}
OPENING: {story.get("opening", "")}
TOTAL ANCHORS TO FIT: {len(story.get("voLines") or [])}

Requirements:
- 40-60 words maximum
- Describe walls, floor, ceiling, doorways, windows, general surfaces, and materials only
- No people, no named props, no medical equipment, no signs, no text
- Wide establishing shot with clear zones"""


async def anthropic_text(
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
) -> str:
    response = await client.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=httpx.Timeout(180.0, connect=10.0),
    )
    response.raise_for_status()
    payload = response.json()
    parts = payload.get("content") or []
    return "\n".join(part.get("text", "") for part in parts if part.get("type") == "text").strip()


def make_bundle(
    topic: TopicCase,
    story: dict[str, Any],
    room_description: str,
    model: str,
    director_prompt: str | None = None,
) -> dict[str, Any]:
    bundle = {
        "_format": "mnemorized-forge-bundle-v1",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "topic": topic.prompt,
        "model": model,
        "story": story,
        "image_prompts": {
            "prompt1": f"{room_description}, aspect ratio 16:9, flat 2D cartoon",
            "prompt2": "",
        },
        "quality_gate": "Local stress harness: provider story generation only; medical citation gate not run.",
        "generated_images": {},
    }
    bundle["image_prompts"] = refreshed_prompts(bundle)
    if director_prompt:
        bundle["image_prompts"]["prompt2_original"] = bundle["image_prompts"]["prompt2"]
        bundle["image_prompts"]["prompt2"] = director_prompt
    return bundle


def inline_image_part(image_path: Path, mime_type: str = "image/png") -> dict[str, Any]:
    return {
        "inlineData": {
            "mimeType": mime_type,
            "data": base64.b64encode(image_path.read_bytes()).decode("ascii"),
        }
    }


async def gemini_generate_image(
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    prompts: list[str],
    output_dir: Path,
    prefix: str,
    seed_image: Path | None = None,
    seed_prompt: str | None = None,
) -> Path:
    api_url = f"{GEMINI_API_BASE}/{model}:generateContent"
    conversation: list[dict[str, Any]] = []
    image_path: Path | None = None

    if seed_image and seed_prompt:
        prompts = [seed_prompt]

    for index, prompt in enumerate(prompts, start=1):
        parts: list[dict[str, Any]] = [{"text": prompt}]
        if seed_image and seed_prompt:
            parts.append(inline_image_part(seed_image))
        conversation.append({"role": "user", "parts": parts})
        body = {
            "contents": conversation,
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }
        for attempt in range(1, 4):
            response = await client.post(
                api_url,
                params={"key": api_key},
                json=body,
                timeout=httpx.Timeout(180.0, connect=10.0),
            )
            if response.status_code == 200:
                break
            if response.status_code in (429, 503) and attempt < 3:
                wait = 30 * attempt
                print(f"  Gemini image {response.status_code}, retry in {wait}s (attempt {attempt}/3)", flush=True)
                time.sleep(wait)
                continue
            raise RuntimeError(f"Gemini image HTTP {response.status_code}: {response.text[:500]}")
        payload = response.json()
        candidates = payload.get("candidates") or []
        parts_out = candidates[0].get("content", {}).get("parts", []) if candidates else []
        image_data = next((part.get("inlineData") for part in parts_out if part.get("inlineData")), None)
        if not image_data or not image_data.get("data"):
            raise RuntimeError(f"Gemini returned no image for prompt {index}: {json.dumps(payload)[:500]}")
        mime = image_data.get("mimeType", "image/png")
        ext = ".png" if "png" in mime else ".jpg"
        image_path = output_dir / f"{prefix}_prompt{index}{ext}"
        image_path.write_bytes(base64.b64decode(image_data["data"]))
        conversation.append({"role": "model", "parts": [{"inlineData": image_data}]})

    if image_path is None:
        raise RuntimeError("Gemini image generation produced no output.")
    return image_path


def anchor_table(story: dict[str, Any]) -> str:
    lines: list[str] = []
    for anchor in story.get("voLines") or []:
        lines.append(f"Anchor {anchor.get('n')}")
        lines.append(f"HOOK: {anchor.get('hook', '')}")
        lines.append(f"VISUAL: {anchor.get('visual', '')}")
        lines.append(f"ENCODES: {anchor.get('anchor', '')}")
        lines.append("")
    return "\n".join(lines).strip()


def compact_fact(text: str, limit: int = 150) -> str:
    fact = re.sub(r"\s+", " ", text or "").strip()
    if len(fact) <= limit:
        return fact
    return fact[: limit - 1].rstrip(" ,;") + "…"


def deterministic_overlay_image(image_path: Path, story: dict[str, Any], output_path: Path) -> Path:
    """Add a deterministic recall strip so exact medical facts are not AI-rendered pixels.

    Gemini is useful for the memory-scene art layer, but it is not reliable at
    rendering exact thresholds, units, and formulas. This composite keeps the
    art layer intact and adds verifiable fact text in a controlled renderer.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:  # pragma: no cover - depends on local tool env
        raise RuntimeError("Pillow is required for deterministic overlay output. Install with `python -m pip install pillow`.") from exc

    base = Image.open(image_path).convert("RGB")
    width, height = base.size
    anchors = list(story.get("voLines") or [])
    if not anchors:
        base.save(output_path)
        return output_path

    font_candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
    ]
    bold_candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf"),
    ]

    def load_font(candidates: list[Path], size: int) -> Any:
        for candidate in candidates:
            if candidate.exists():
                return ImageFont.truetype(str(candidate), size=size)
        return ImageFont.load_default()

    title_font = load_font(bold_candidates, max(22, width // 54))
    body_font = load_font(font_candidates, max(18, width // 70))
    badge_font = load_font(bold_candidates, max(18, width // 68))

    margin = max(20, width // 48)
    gap = max(10, width // 120)
    columns = 2 if width >= 1000 and len(anchors) > 1 else 1
    col_width = (width - margin * 2 - gap * (columns - 1)) // columns
    line_chars = max(34, col_width // max(9, body_font.size // 2))

    wrapped: list[list[str]] = []
    for anchor in anchors:
        fact = compact_fact(str(anchor.get("anchor") or anchor.get("visual") or ""), 180)
        wrapped.append(textwrap.wrap(fact, width=line_chars, max_lines=3, placeholder="…"))

    card_h = max(78, body_font.size * 4 + 18)
    rows = (len(anchors) + columns - 1) // columns
    strip_h = margin * 2 + title_font.size + 14 + rows * card_h + (rows - 1) * gap

    canvas = Image.new("RGB", (width, height + strip_h), (12, 18, 18))
    canvas.paste(base, (0, 0))
    draw = ImageDraw.Draw(canvas)
    strip_y = height
    draw.rectangle([0, strip_y, width, height + strip_h], fill=(11, 17, 17))
    draw.line([0, strip_y, width, strip_y], fill=(190, 255, 70), width=max(2, width // 500))
    draw.text(
        (margin, strip_y + margin),
        "Verified recall strip - exact protocol facts rendered deterministically",
        fill=(210, 255, 95),
        font=title_font,
    )

    start_y = strip_y + margin + title_font.size + 14
    for index, anchor in enumerate(anchors):
        row = index // columns
        col = index % columns
        x = margin + col * (col_width + gap)
        y = start_y + row * (card_h + gap)
        draw.rounded_rectangle(
            [x, y, x + col_width, y + card_h],
            radius=10,
            fill=(18, 28, 28),
            outline=(64, 86, 72),
            width=1,
        )
        badge_size = max(30, body_font.size + 12)
        badge_x = x + 12
        badge_y = y + 12
        draw.ellipse(
            [badge_x, badge_y, badge_x + badge_size, badge_y + badge_size],
            fill=(125, 160, 24),
            outline=(210, 255, 95),
            width=1,
        )
        n = str(anchor.get("n") or index + 1)
        bbox = draw.textbbox((0, 0), n, font=badge_font)
        draw.text(
            (badge_x + (badge_size - (bbox[2] - bbox[0])) / 2, badge_y + (badge_size - (bbox[3] - bbox[1])) / 2 - 1),
            n,
            fill=(245, 255, 220),
            font=badge_font,
        )
        text_x = badge_x + badge_size + 12
        text_y = y + 12
        for line in wrapped[index]:
            draw.text((text_x, text_y), line, fill=(236, 241, 230), font=body_font)
            text_y += body_font.size + 6

    canvas.save(output_path)
    return output_path


def audit_prompt(
    story: dict[str, Any],
    visual_prompt: str | None = None,
    deterministic_overlay: bool = False,
) -> str:
    visual_source = (
        f"""DIRECTOR VISUAL PROMPT:

{visual_prompt}

"""
        if visual_prompt
        else ""
    )
    visual_rule = (
        "Use the DIRECTOR VISUAL PROMPT as the visual source of truth. Use the anchor table to verify clinical coverage. "
        "Do not penalize the image for differing from the anchor table's original VISUAL wording when the director prompt uses a safer or clearer visual for the same fact."
        if visual_prompt
        else "Use the anchor table as the visual source of truth."
    )
    overlay_rule = (
        "\nThis image may include a deterministic verified recall strip below the generated art layer. Treat exact facts in that strip as valid for medical-fact accuracy and label accuracy. Still require the art layer to contain recognizable visual mnemonic cues for each numbered fact."
        if deterministic_overlay
        else ""
    )
    return f"""You are the external auditor for a generated Mnemorized medical visual mnemonic image.

{visual_rule}{overlay_rule}

Grade with the CANONICAL RUBRIC below (the same standard used in-app and in
docs/image-scoring-rubric.md). Score by the arithmetic, not by impression.
Numbers, doses, units, thresholds, and formulas must NOT appear as drawn text — the
image carries a hook for the concept and the exact value lives in the narration/
flashcards. A spelled-out value on a plaque/gauge/dial (e.g. "30 mL/kg", "MAP 65") is a
text-discipline defect (category D), not correct. A number is acceptable only when
encoded as a hook (a shape look-alike or a countable quantity), never as digits.

{CANONICAL_RUBRIC}

Return the required scoreblock EXACTLY, with OVERALL_SCORE = min(RAW_SUM, lowest gate cap):

{RUBRIC_OUTPUT_FORMAT}

Then add these supporting sections:
SUMMARY: [2-4 sentences]
ANCHOR_AUDIT:
| # | Present? | Hook fidelity | Silhouette/readability | Text/label accuracy | Medical risk | Fix |
|---|---|---|---|---|---|---|
SYSTEMIC_FAILURES:
- [repeatable failures only, or None.]
REPAIR_PROMPT:
[If REPAIR, write an image-edit prompt. Otherwise N/A.]
REGENERATION_PROMPT_CHANGE:
[If systemic regeneration needed, write prompt change. Otherwise N/A.]

{visual_source}ANCHOR TABLE:

{anchor_table(story)}
"""


def director_repair_system_prompt() -> str:
    return f"""You are the visual director for Mnemorized medical mnemonic images.

You are REWRITING a visual director prompt that Gemini failed to render correctly.
You have the original prompt and the audit feedback explaining what went wrong.

Your job: rewrite the ENTIRE image prompt from scratch, keeping what worked and REPLACING what failed with a different, simpler visual strategy that Gemini CAN draw.

{GEMINI_CAPABILITY_RULES}

KEY RULES:
1. Do NOT repeat the same instruction that failed. If the audit says "X was not rendered correctly," find a DIFFERENT visual metaphor for the same medical fact.
2. The rewritten prompt must be SHORTER or equal in length to the original. Never add detail — remove or replace.
3. Spatial precision beyond left/center/right and top/middle/bottom is WASTED on Gemini. Use relative terms only.
4. Do not specify character micro-poses. Gemini ignores them and the extra text dilutes useful instructions.
5. Keep the prompt under 10 short paragraphs. Write a camera brief, not a novel.
6. Write ALL scene directions and emphasis in lowercase. Only ALL-CAPS for labels that must appear in the image.
7. For every required text label, use: "a large brass plaque bolted to [object] reads [LABEL] in bold block letters."
8. Always end with the text allowlist fence: "Visible text limited to: [list]. No other text..."
9. Rewrite the COMPLETE prompt, not a repair patch — targeted repairs cause previously-working elements to be dropped.

Return ONLY:
<image_prompt>...</image_prompt>
"""


def director_repair_user_prompt(
    original_prompt: str,
    audit_text: str,
    story: dict[str, Any],
) -> str:
    return f"""Rewrite this Gemini image prompt. The original was partially successful but had failures.

ORIGINAL PROMPT:
{original_prompt}

AUDIT FEEDBACK:
{audit_text}

ANCHOR TABLE (what must be encoded):
{anchor_table(story)}

Rewrite the full image prompt. Keep everything that worked. For each failure described in the audit, use a DIFFERENT, SIMPLER visual strategy. Do not repeat the failed instruction. Write a complete replacement prompt, not a diff."""


def parse_audit_score(text: str) -> tuple[int, str]:
    """Deterministically recompute OVERALL = min(RAW_SUM, gate caps) from the
    auditor's own reported fields, so an inflated OVERALL line cannot pass the gate.
    Falls back to the model's OVERALL_SCORE only when no RAW_SUM/gates are present."""
    model_match = re.search(r"OVERALL_SCORE\s*:\s*(\d{1,3})", text, flags=re.I)
    raw_match = re.search(r"RAW_SUM\s*:\s*(\d{1,3})", text, flags=re.I)
    gates_match = re.search(r"GATES_TRIGGERED\s*:\s*(.+)", text, flags=re.I)
    missing_match = re.search(r"MISSING_ANCHORS\s*:\s*(.+)", text, flags=re.I)
    # PASS_WITH_TEXT_RISK must be matched before bare PASS.
    decision_match = re.search(
        r"DECISION\s*:\s*(PASS_WITH_TEXT_RISK|PASS|REPAIR|REGENERATE)", text, flags=re.I
    )

    model_score = int(model_match.group(1)) if model_match else None
    raw_sum = int(raw_match.group(1)) if raw_match else None
    gates = (gates_match.group(1) if gates_match else "").upper()

    missing_count = 0
    if missing_match:
        raw_missing = missing_match.group(1).strip()
        if raw_missing and not re.fullmatch(r"none", raw_missing, flags=re.I):
            missing_count = len([p for p in raw_missing.split(",") if p.strip()])

    caps: list[int] = []
    if raw_sum is not None:
        caps.append(raw_sum)
    caps.append(_g1_cap(missing_count))
    for gate, cap in _GATE_CAPS.items():
        if gate in gates:
            caps.append(cap)

    if raw_sum is None and len(caps) <= 1:
        # No rubric arithmetic available; fall back to the model's own number.
        score = model_score if model_score is not None else 0
    else:
        score = min(caps)

    decision = decision_match.group(1).upper() if decision_match else "REGENERATE"
    return min(max(score, 0), 100), decision


def extract_section(text: str, name: str) -> str:
    match = re.search(
        fr"{name}\s*:\s*(.*?)(?=\n[A-Z_]+\s*:|\Z)",
        text,
        flags=re.I | re.S,
    )
    return match.group(1).strip() if match else ""


async def gemini_audit_image(
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    image_path: Path,
    story: dict[str, Any],
    visual_prompt: str | None = None,
    deterministic_overlay: bool = False,
) -> str:
    api_url = f"{GEMINI_API_BASE}/{model}:generateContent"
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": audit_prompt(story, visual_prompt=visual_prompt, deterministic_overlay=deterministic_overlay)},
                    inline_image_part(image_path),
                ],
            }
        ]
    }
    for attempt in range(1, 4):
        response = await client.post(
            api_url,
            params={"key": api_key},
            json=body,
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
        if response.status_code == 200:
            break
        if response.status_code in (429, 503) and attempt < 3:
            wait = 30 * attempt
            print(f"  Gemini audit {response.status_code}, retry in {wait}s (attempt {attempt}/3)", flush=True)
            time.sleep(wait)
            continue
        raise RuntimeError(f"Gemini audit HTTP {response.status_code}: {response.text[:500]}")
    payload = response.json()
    candidates = payload.get("candidates") or []
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    return "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()


def topic_cases(selected: list[str] | None = None) -> list[TopicCase]:
    if not selected:
        return DEFAULT_TOPICS
    selected_set = {slugify(item) for item in selected}
    return [topic for topic in DEFAULT_TOPICS if topic.slug in selected_set or slugify(topic.title) in selected_set]


async def run_topic(
    topic: TopicCase,
    env: dict[str, str],
    output_root: Path,
    max_iterations: int,
    target_score: int,
    skip_images: bool,
    plate_size: int,
    deterministic_overlay: bool,
    use_image_edit_repair: bool,
    start_plate: int = 1,
) -> dict[str, Any]:
    topic_dir = output_root / topic.slug
    topic_dir.mkdir(parents=True, exist_ok=True)
    model = env.get("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL)
    image_model = env.get("GEMINI_MODEL", DEFAULT_GEMINI_IMAGE_MODEL)
    audit_model = env.get("GEMINI_AUDIT_MODEL", DEFAULT_GEMINI_AUDIT_MODEL)

    async with httpx.AsyncClient() as client:
        story_raw_path = topic_dir / "story_raw.xml"
        room_desc_path = topic_dir / "room_description.txt"
        director_path = topic_dir / "visual_director_prompt.txt"
        can_reuse = start_plate > 1 and story_raw_path.exists() and room_desc_path.exists()

        if can_reuse:
            story_raw = story_raw_path.read_text(encoding="utf-8")
            story = parse_story_xml(story_raw)
            room_description = room_desc_path.read_text(encoding="utf-8")
            director_prompt = director_path.read_text(encoding="utf-8") if director_path.exists() else ""
            print(f"  REUSE existing story ({len(story['voLines'])} anchors)", flush=True)
        else:
            story_raw = ""
            story = {"voLines": []}
            for story_attempt in range(1, 4):
                extra = ""
                if story_attempt > 1:
                    extra = (
                        "\n\nYour previous response was invalid because it included planning text or did not produce 8-10 "
                        "<vo_line> blocks. Output ONLY the required XML tags now. No <thinking>, no markdown, no headings."
                    )
                story_raw = await anthropic_text(
                    client,
                    env["ANTHROPIC_API_KEY"],
                    model,
                    story_system_prompt(),
                    story_user_prompt(topic) + extra,
                    max_tokens=4096,
                )
                story = parse_story_xml(story_raw)
                if 8 <= len(story["voLines"]) <= 10:
                    break
            story_raw_path.write_text(story_raw, encoding="utf-8")
            if not 8 <= len(story["voLines"]) <= 10:
                raise RuntimeError(f"{topic.title}: expected 8-10 anchors, got {len(story['voLines'])}")

            room_raw = await anthropic_text(
                client,
                env["ANTHROPIC_API_KEY"],
                model,
                "You write empty-room scene descriptions for visual mnemonic image generation.",
                room_user_prompt(topic, story),
                max_tokens=300,
            )
            room_description = re.sub(r"\s+", " ", room_raw).strip()
            room_desc_path.write_text(room_description, encoding="utf-8")

            director_raw = await anthropic_text(
                client,
                env["ANTHROPIC_API_KEY"],
                model,
                visual_director_system_prompt(),
                visual_director_user_prompt(topic, story, room_description),
                max_tokens=3000,
            )
            director_prompt = tag_text(director_raw, "image_prompt") or strip_code_fences(director_raw)
            director_path.write_text(director_prompt, encoding="utf-8")

        bundle = make_bundle(topic, story, room_description, model, director_prompt=director_prompt)
        bundle_path = topic_dir / f"{topic.slug}_bundle.json"
        bundle_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        pack_dir = build_pack(bundle_path, output_root / "_visual_qa_packs", refresh_prompt_contract=False)

        result: dict[str, Any] = {
            "topic": topic.title,
            "bundle": str(bundle_path),
            "pack": str(pack_dir),
            "anchors": len(story["voLines"]),
            "iterations": [],
            "passed": False,
        }
        if skip_images:
            return result

        prompt1 = (pack_dir / "01_gemini_prompt_1_scene_foundation.txt").read_text(encoding="utf-8")
        result["plates"] = []
        plates = split_anchor_plates(story, plate_size=plate_size)
        for plate_index, plate_story in enumerate(plates, start=1):
            if plate_index < start_plate:
                audit_file = topic_dir / f"plate_{plate_index}" / f"iter{max_iterations}_audit.txt"
                for i in range(max_iterations, 0, -1):
                    candidate = topic_dir / f"plate_{plate_index}" / f"iter{i}_audit.txt"
                    if candidate.exists():
                        audit_file = candidate
                        break
                if audit_file.exists():
                    score, decision = parse_audit_score(audit_file.read_text(encoding="utf-8"))
                    result["plates"].append({"plate": plate_index, "passed": decision == "PASS", "skipped": True})
                    print(f"  SKIP plate {plate_index} (prior score {score}, {decision})", flush=True)
                else:
                    result["plates"].append({"plate": plate_index, "passed": False, "skipped": True})
                    print(f"  SKIP plate {plate_index} (no prior audit)", flush=True)
                continue
            plate_label = f"Plate {plate_index} of {len(plates)}"
            plate_dir = topic_dir / f"plate_{plate_index}"
            plate_dir.mkdir(parents=True, exist_ok=True)
            plate_prompt_raw = await anthropic_text(
                client,
                env["ANTHROPIC_API_KEY"],
                model,
                visual_director_system_prompt(),
                visual_director_user_prompt(topic, plate_story, room_description, plate_label=plate_label),
                max_tokens=2600,
            )
            prompt2_base = tag_text(plate_prompt_raw, "image_prompt") or strip_code_fences(plate_prompt_raw)
            (plate_dir / "visual_director_prompt.txt").write_text(prompt2_base, encoding="utf-8")
            prompt2 = prompt2_base
            current_image: Path | None = None
            plate_result: dict[str, Any] = {
                "plate": plate_index,
                "anchors": [anchor.get("n") for anchor in plate_story.get("voLines", [])],
                "prompt": str(plate_dir / "visual_director_prompt.txt"),
                "iterations": [],
                "passed": False,
            }

            for iteration in range(1, max_iterations + 1):
                prefix = f"plate{plate_index}_iter{iteration}"
                if current_image is not None and use_image_edit_repair:
                    repair_prompt = plate_result["iterations"][-1].get("repair_prompt", "")
                    if repair_prompt and repair_prompt.upper() != "N/A":
                        current_image = await gemini_generate_image(
                            client,
                            env["GEMINI_API_KEY"],
                            image_model,
                            [],
                            plate_dir,
                            prefix,
                            seed_image=current_image,
                            seed_prompt=repair_prompt,
                        )
                    else:
                        current_image = await gemini_generate_image(
                            client,
                            env["GEMINI_API_KEY"],
                            image_model,
                            [prompt1, prompt2],
                            plate_dir,
                            prefix,
                        )
                else:
                    current_image = await gemini_generate_image(
                        client,
                        env["GEMINI_API_KEY"],
                        image_model,
                        [prompt1, prompt2],
                        plate_dir,
                        prefix,
                    )

                audit_image = current_image
                composite_path: Path | None = None
                if deterministic_overlay:
                    composite_path = plate_dir / f"{prefix}_verified_composite.png"
                    audit_image = deterministic_overlay_image(current_image, plate_story, composite_path)

                audit_text = await gemini_audit_image(
                    client,
                    env["GEMINI_API_KEY"],
                    audit_model,
                    audit_image,
                    plate_story,
                    visual_prompt=prompt2_base,
                    deterministic_overlay=deterministic_overlay,
                )
                audit_path = plate_dir / f"iter{iteration}_audit.txt"
                audit_path.write_text(audit_text, encoding="utf-8")
                score, decision = parse_audit_score(audit_text)
                repair_prompt = extract_section(audit_text, "REPAIR_PROMPT")
                regen_change = extract_section(audit_text, "REGENERATION_PROMPT_CHANGE")
                iteration_result = {
                    "iteration": iteration,
                    "image": str(current_image),
                    "audit_image": str(audit_image),
                    "verified_composite": str(composite_path) if composite_path else None,
                    "audit": str(audit_path),
                    "score": score,
                    "decision": decision,
                    "repair_prompt": repair_prompt,
                    "regeneration_prompt_change": regen_change,
                }
                plate_result["iterations"].append(iteration_result)
                result["iterations"].append({"plate": plate_index, **iteration_result})
                if score >= target_score and decision == "PASS":
                    plate_result["passed"] = True
                    break
                should_regenerate = (
                    not use_image_edit_repair
                    or
                    decision == "REGENERATE"
                    or score < 55
                    or len(repair_prompt) > 1200
                    or not repair_prompt
                    or repair_prompt.upper() == "N/A"
                )
                if should_regenerate:
                    rewritten_raw = await anthropic_text(
                        client,
                        env["ANTHROPIC_API_KEY"],
                        model,
                        director_repair_system_prompt(),
                        director_repair_user_prompt(prompt2_base, audit_text, plate_story),
                        max_tokens=2600,
                    )
                    rewritten = tag_text(rewritten_raw, "image_prompt") or strip_code_fences(rewritten_raw)
                    if rewritten and len(rewritten) > 100:
                        prompt2 = rewritten
                        prompt2_base = rewritten
                        (plate_dir / f"director_repair_iter{iteration}.txt").write_text(
                            rewritten, encoding="utf-8",
                        )
                    else:
                        prompt2 = f"{prompt2_base}\n\nADDITIONAL REGENERATION FIX:\n{repair_prompt}\n"
                    current_image = None
                time.sleep(1)
            result["plates"].append(plate_result)

        result["passed"] = all(plate.get("passed") for plate in result["plates"])

        return result


def assemble_plate_set(result: dict[str, Any], output_dir: Path) -> Path | None:
    """Stitch passing plate composites into a single publishable plate-set image."""
    try:
        from PIL import Image
    except ImportError:
        return None

    plates = result.get("plates") or []
    passing: list[Path] = []
    for plate in plates:
        if not plate.get("passed"):
            continue
        for iteration in reversed(plate.get("iterations", [])):
            composite = iteration.get("verified_composite")
            if composite and Path(composite).exists():
                passing.append(Path(composite))
                break

    if not passing:
        return None

    images = [Image.open(path).convert("RGB") for path in passing]
    widths = [img.width for img in images]
    max_width = max(widths)
    total_height = sum(img.height for img in images)

    canvas = Image.new("RGB", (max_width, total_height), (12, 18, 18))
    y = 0
    for img in images:
        x = (max_width - img.width) // 2
        canvas.paste(img, (x, y))
        y += img.height

    set_path = output_dir / "publishable_plate_set.png"
    canvas.save(set_path)
    return set_path


async def async_main() -> int:
    parser = argparse.ArgumentParser(description="Stress-test Mnemorized visual mnemonic generation.")
    parser.add_argument("--env", type=Path, default=Path("backend/.env"))
    parser.add_argument("--output-root", type=Path, default=Path("Troubleshooting Prompts") / "three_topic_stress")
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--target-score", type=int, default=TARGET_SCORE)
    parser.add_argument("--plate-size", type=int, default=3, help="Anchors per generated image plate.")
    parser.add_argument("--no-deterministic-overlay", action="store_true", help="Audit raw Gemini images without the exact-fact recall strip.")
    parser.add_argument("--use-image-edit-repair", action="store_true", help="Try Gemini image-edit repair before regenerating. Default regenerates from prompt guidance because image edits are less stable.")
    parser.add_argument("--skip-images", action="store_true", help="Generate bundles and QA packs only.")
    parser.add_argument("--topic", action="append", help="Run only a default topic by slug or title.")
    parser.add_argument("--start-plate", type=int, default=1, help="Skip plates before this index (1-based). Useful for resuming.")
    args = parser.parse_args()

    env = load_env(args.env)
    missing = [key for key in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY") if not env.get(key)]
    if missing and not args.skip_images:
        raise SystemExit(f"Missing required env key(s): {', '.join(missing)}")
    if not env.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Missing ANTHROPIC_API_KEY.")

    args.output_root.mkdir(parents=True, exist_ok=True)
    results = []
    for topic in topic_cases(args.topic):
        print(f"RUN {topic.title}", flush=True)
        result = await run_topic(
            topic,
            env,
            args.output_root,
            args.max_iterations,
            args.target_score,
            args.skip_images,
            args.plate_size,
            deterministic_overlay=not args.no_deterministic_overlay,
            use_image_edit_repair=args.use_image_edit_repair,
            start_plate=args.start_plate,
        )
        results.append(result)
        best = max((item["score"] for item in result["iterations"]), default=None)
        plate_set = assemble_plate_set(result, args.output_root / topic.slug)
        if plate_set:
            result["plate_set"] = str(plate_set)
            print(f"ASSEMBLED {plate_set}", flush=True)
        print(f"DONE {topic.slug} passed={result['passed']} best={best}", flush=True)

    summary_path = args.output_root / "stress_summary.json"
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(summary_path)
    return 0 if all(result["passed"] or args.skip_images for result in results) else 2


def main() -> int:
    import asyncio

    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
