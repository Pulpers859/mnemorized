from __future__ import annotations

import json
from pathlib import Path

from tools.visual_qa_pack import audit_bundle, build_pack


def make_bundle() -> dict:
    anchors = []
    for index in range(1, 9):
        anchors.append(
            {
                "n": index,
                "hook": "functional — key opens lock to encode agonism",
                "narration": f"Notice anchor {index}.",
                "visual": f"Key-shaped character opening lock at zone {index}",
                "anchor": f"Clinical fact {index}",
            }
        )
    return {
        "_format": "mnemorized-forge-bundle-v1",
        "topic": "test topic",
        "story": {
            "scene_title": "Test Tavern",
            "opening": "A test scene.",
            "voLines": anchors,
            "review_script": "\n".join(f"When you see anchor {i} — remember fact {i}" for i in range(1, 9)),
        },
        "image_prompts": {
            "prompt1": "room foundation",
            "prompt2": (
                'The words "Hook" and "Encodes" are invisible design guidance only. '
                "Preserve clear spatial hierarchy. Hook: functional. Encodes: Clinical fact."
            ),
        },
    }


def test_visual_qa_pack_writes_gemini_prompts_and_rubric(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(make_bundle()), encoding="utf-8")

    pack_dir = build_pack(bundle_path, tmp_path / "packs")

    assert (pack_dir / "01_gemini_prompt_1_scene_foundation.txt").read_text(encoding="utf-8") == "room foundation\n"
    assert "Hook" in (pack_dir / "02_gemini_prompt_2_all_anchors.txt").read_text(encoding="utf-8")
    assert "Anchor Table" in (pack_dir / "03_anchor_table.md").read_text(encoding="utf-8")
    assert "Manual Image Audit" in (pack_dir / "05_manual_image_audit.md").read_text(encoding="utf-8")
    assert "qualitative sandbox" in (pack_dir / "00_README.md").read_text(encoding="utf-8")


def test_visual_qa_pack_flags_missing_hooks_and_text_heavy_visuals() -> None:
    bundle = make_bundle()
    bundle["story"]["voLines"][0]["hook"] = ""
    bundle["story"]["voLines"][1]["visual"] = 'Poster labeled "one two three four five six seven eight nine" on wall'
    bundle["image_prompts"]["prompt1"] = "Style reference: Sketchy Medical"
    bundle["image_prompts"]["prompt2"] = "Hook: functional. Encodes: fact."

    score, findings = audit_bundle(bundle)
    codes = {finding.code for finding in findings}

    assert score < 85
    assert "missing_hooks" in codes
    assert "text_dependent_visuals" in codes
    assert "hook_may_render" in codes
    assert "brand_style_reference" in codes
