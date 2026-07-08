"""Composite exact precision text onto a generated palace image — deterministically.

WHY THIS EXISTS
---------------
Diffusion/AR image models cannot reliably spell. Numbers, doses, thresholds, and
formulas (the rubric's "precision text": 340 mOsm, 0.1 U/kg/hr, QRS >100,
Na-(Cl+HCO3)) are exact facts with no visual substitute, and the model garbles
them (gate G2). The fix is to NOT let the model draw that text at all: generate the
image with BLANK plaques/dials/tags, then draw the exact text here as a vector layer.

SCOPE — PRECISION ONLY, BY DESIGN.
This tool renders numbers/units/formulas. It deliberately does NOT provide a general
labeling channel: ordinary words, drug names, and mnemonic terms must be carried by a
visual hook, not text. Keeping the overlay precision-only means it REMOVES labels
(everything non-numeric becomes a hook) rather than proliferating them.

USAGE
-----
    python tools/overlay_precision_labels.py --image in.png --spec spec.json --out out.png

spec.json is a list of placements, each:
    {"text": "340 mOsm", "cx": 1290, "cy": 545, "w": 150,
     "rot": -4, "style": "plaque"}
  cx,cy = center in pixels; w = target text box width in px; rot = degrees (optional);
  style = "plaque" (parchment sign, default) | "chalk" (dark slate) | "dial" (round).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "C:/Windows/Fonts/comicbd.ttf",  # Comic Sans Bold — matches the marker aesthetic
    "C:/Windows/Fonts/comic.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

STYLES = {
    # bg fill, text fill, border fill  (RGBA)
    "plaque": ((244, 233, 202, 255), (40, 30, 20, 255), (60, 42, 26, 255)),
    "chalk": ((38, 42, 46, 255), (238, 240, 236, 255), (20, 22, 24, 255)),
    "dial": ((248, 244, 236, 255), (30, 24, 18, 255), (70, 50, 30, 255)),
}


def _load_font(px: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, px)
    return ImageFont.load_default()


def _fit_font(text: str, target_w: int, max_px: int = 96, min_px: int = 14) -> ImageFont.FreeTypeFont:
    """Largest font whose rendered width fits target_w."""
    probe = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(probe)
    for px in range(max_px, min_px - 1, -2):
        font = _load_font(px)
        w = d.textbbox((0, 0), text, font=font)[2]
        if w <= target_w:
            return font
    return _load_font(min_px)


def _draw_one(base: Image.Image, place: dict) -> None:
    text = str(place["text"])
    cx, cy = int(place["cx"]), int(place["cy"])
    target_w = int(place.get("w", 160))
    rot = float(place.get("rot", 0))
    style = place.get("style", "plaque")
    bg, fg, border = STYLES.get(style, STYLES["plaque"])

    font = _fit_font(text, target_w)

    # measure text
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    l, t, r, b = probe.textbbox((0, 0), text, font=font)
    tw, th = r - l, b - t
    pad_x, pad_y = max(10, th // 2), max(6, th // 3)
    tile_w, tile_h = tw + 2 * pad_x, th + 2 * pad_y

    tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    if style == "dial":
        td.ellipse([0, 0, tile_w - 1, tile_h - 1], fill=bg, outline=border, width=max(3, th // 12))
    else:
        rad = max(6, th // 4)
        td.rounded_rectangle([0, 0, tile_w - 1, tile_h - 1], radius=rad, fill=bg,
                             outline=border, width=max(3, th // 14))
    td.text((pad_x - l, pad_y - t), text, font=font, fill=fg)

    if rot:
        tile = tile.rotate(rot, expand=True, resample=Image.BICUBIC)

    base.alpha_composite(tile, (cx - tile.width // 2, cy - tile.height // 2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = Image.open(args.image).convert("RGBA")
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    if not isinstance(spec, list):
        raise SystemExit("spec must be a JSON list of placements")

    for place in spec:
        _draw_one(base, place)

    out = Path(args.out)
    base.convert("RGB").save(out, quality=95)
    print(f"wrote {out} ({len(spec)} labels)")


if __name__ == "__main__":
    main()
