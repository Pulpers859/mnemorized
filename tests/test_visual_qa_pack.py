from __future__ import annotations

import json
from pathlib import Path

from tools.visual_qa_pack import audit_bundle, build_pack, condense_for_image, refreshed_prompts, visible_text_surface_count


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
    assert "OVERALL_SCORE" in (pack_dir / "07_gemini_image_audit_prompt.txt").read_text(encoding="utf-8")
    assert "Rewrite the ENTIRE director prompt from scratch" in (pack_dir / "08_repair_or_regenerate_prompt_template.txt").read_text(encoding="utf-8")
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


def test_visual_qa_pack_flags_unquoted_label_piles() -> None:
    bundle = make_bundle()
    bundle["story"]["voLines"][0]["visual"] = (
        "Armory rack with key labeled P2Y12, fishnet labeled UFH/LMWH, "
        "banner reads CHEW FIRST, plaque stamped 90 MIN"
    )

    score, findings = audit_bundle(bundle)
    codes = {finding.code for finding in findings}

    assert visible_text_surface_count(bundle["story"]["voLines"][0]["visual"]) > 2
    assert score < 100
    assert "too_many_text_surfaces" in codes


def test_visual_qa_pack_flags_visual_meta_leak_without_overcounting_no_labels() -> None:
    bundle = make_bundle()
    bundle["story"]["voLines"][0]["visual"] = "Cracked eyeball bottle at left wall. No text labels."

    score, findings = audit_bundle(bundle)
    codes = {finding.code for finding in findings}

    assert visible_text_surface_count(bundle["story"]["voLines"][0]["visual"]) == 0
    assert score < 100
    assert "visual_meta_leak" in codes


def test_refreshed_prompt_contract_preserves_compact_formulas() -> None:
    bundle = make_bundle()
    bundle["image_prompts"]["prompt1"] = "old style\n\nWide room, aspect ratio 16:9"
    bundle["story"]["voLines"][0]["visual"] = 'Scale beam labeled "Expected pCO₂ = 1.5 × HCO₃ + 8 ± 2" at foreground'

    prompts = refreshed_prompts(bundle)

    assert "PRECISION TEXT EXCEPTION" in prompts["prompt2"]
    assert "ANCHOR LEGIBILITY RULE" in prompts["prompt2"]
    assert "EXACT LABEL RULE" in prompts["prompt2"]
    assert "Expected pCO₂ = 1.5 × HCO₃ + 8 ± 2" in prompts["prompt2"]
    assert "No formulas" not in prompts["prompt2"]


def test_condense_for_image_does_not_treat_closing_quote_as_opening_quote() -> None:
    visual = 'Left pan labeled "Na+," right pan holds weights "Cl−" and "HCO3−."'

    assert condense_for_image(visual) == visual


def test_gemini_image_audit_prompt_contains_anchor_table(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(make_bundle()), encoding="utf-8")

    pack_dir = build_pack(bundle_path, tmp_path / "packs")
    audit_prompt = (pack_dir / "07_gemini_image_audit_prompt.txt").read_text(encoding="utf-8")

    assert "ANCHOR_AUDIT:" in audit_prompt
    assert "SYSTEMIC_FAILURES:" in audit_prompt
    assert "REPAIR_PROMPT:" in audit_prompt
    assert "Anchor 1" in audit_prompt
    assert "HOOK: functional" in audit_prompt
    assert "ENCODES: Clinical fact 1" in audit_prompt
