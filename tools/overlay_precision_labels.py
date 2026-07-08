"""Composite exact precision text onto a generated palace image — deterministically.

WHY THIS EXISTS
---------------
Diffusion/AR image models cannot reliably spell. Numbers, doses, thresholds, and
formulas (the rubric's "precision text": 340 mOsm, 0.1 U/kg/hr, QRS >100,
Na-(Cl+HCO3)) are exact facts with no visual substitute, and the model garbles
them (gate G2). The fix is to NOT let the model draw that text at all: generate the
image with a small BLANK signpost-gap reserved at each fact's zone, then draw the
exact text here as a self-contained vector tile.

SCOPE — PRECISION ONLY, BY DESIGN.
This tool renders numbers/units/formulas. It deliberately does NOT provide a general
labeling channel: ordinary words, drug names, and mnemonic terms must be carried by a
visual hook, not text. Keeping the overlay precision-only means it REMOVES labels
(everything non-numeric becomes a hook) rather than proliferating them.

PLACEMENT IS DETERMINISTIC — NOT EYEBALLED, NOT DETECTED.
Earlier this tool required hand-measured pixel coordinates (cx, cy, w). Eyeballing
those produced tiles that did not line up with the intended object and did not fit.
The robust fix: place by the SAME zone the generator assigned the anchor. A zone
string ("lower-left", "mid-right", "center", or "rail") resolves to a deterministic
box computed purely from the image size — the identical map the prompt uses when it
tells the model to leave that zone's signpost-gap clear. The tile is self-contained
(it draws its own plaque/tag/dial), so it never has to "fit inside" anything the
model drew; it IS the prop. Multiple facts sharing a zone stack deterministically.
Explicit pixel cx/cy/w still override the zone when you need pixel control.

USAGE
-----
    python tools/overlay_precision_labels.py --image in.png --spec spec.json --out out.png

spec.json is a list of placements. Preferred (deterministic zone) form:
    {"text": "340 mOsm", "zone": "lower-right", "style": "plaque"}
  zone   = vertical keyword (upper/top | mid/center | lower/bottom) + horizontal
           keyword (left | center | right), any order; or "rail" for the reserved
           bottom readout strip. Unknown/absent -> "center".
  style  = "plaque" (parchment sign, default) | "chalk" (dark slate) | "dial" (round).

Explicit-pixel override form (bypasses the zone map):
    {"text": "340 mOsm", "cx": 1290, "cy": 545, "w": 150, "rot": -4, "style": "plaque"}
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


# ── Deterministic zone → box map ────────────────────────────────────
# One source of truth for placement, mirrored by the prompt's "leave a clear
# signpost-gap at <zone>" directive. col/row in {0,1,2} pick a 3x3 cell; the tile
# sits in the lower-middle of its cell so it reads as a tag near the object's base.

def _zone_grid(zone: str) -> tuple[int, int]:
    """Parse a zone string into (col, row), each in {0,1,2}. Defaults to center."""
    z = str(zone or "").lower()
    if "left" in z:
        col = 0
    elif "right" in z:
        col = 2
    else:
        col = 1
    if "upper" in z or "top" in z:
        row = 0
    elif "lower" in z or "bottom" in z:
        row = 2
    else:
        row = 1
    return col, row


def _is_rail(zone: str) -> bool:
    z = str(zone or "").lower()
    return "rail" in z or "readout" in z or "strip" in z


def resolve_boxes(spec: list[dict], img_w: int, img_h: int) -> list[dict]:
    """Return each placement with a concrete (cx, cy, w) resolved deterministically.

    Explicit pixel cx/cy override the zone map. Zone placements are grouped by cell
    (or the rail) and stacked so multiple facts in one zone never overlap. Purely a
    function of the spec order + image size, so it is reproducible run to run.
    """
    # Group indices by their placement bucket so we can stack within a bucket.
    buckets: dict[str, list[int]] = {}
    for i, place in enumerate(spec):
        if "cx" in place and "cy" in place:
            key = f"px:{i}"  # explicit pixels never share a bucket
        elif _is_rail(place.get("zone")):
            key = "rail"
        else:
            col, row = _zone_grid(place.get("zone"))
            key = f"cell:{col},{row}"
        buckets.setdefault(key, []).append(i)

    cell_w, cell_h = img_w / 3.0, img_h / 3.0
    resolved: list[dict] = [dict(p) for p in spec]

    for key, idxs in buckets.items():
        count = len(idxs)
        for slot, i in enumerate(idxs):
            place = resolved[i]
            if key.startswith("px:"):
                place.setdefault("w", 160)
                continue
            if key == "rail":
                # Bottom reserved readout strip: slots left-to-right.
                place["w"] = int(cell_w * 3 / max(count, 1) * 0.8)
                place["cx"] = int(img_w * (slot + 0.5) / count)
                place["cy"] = int(img_h * 0.93)
                continue
            col, row = _zone_grid(place.get("zone"))
            base_cx = col * cell_w + cell_w / 2.0
            # Lower-middle of the cell so the tag sits under its object.
            base_cy = row * cell_h + cell_h * 0.62
            # Stack multiple facts in one cell vertically, centered on base_cy.
            step = cell_h * 0.22
            offset = (slot - (count - 1) / 2.0) * step
            place["w"] = int(cell_w * 0.7)
            place["cx"] = int(base_cx)
            place["cy"] = int(base_cy + offset)
    return resolved


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

    for place in resolve_boxes(spec, base.width, base.height):
        _draw_one(base, place)

    out = Path(args.out)
    base.convert("RGB").save(out, quality=95)
    print(f"wrote {out} ({len(spec)} labels)")


if __name__ == "__main__":
    main()
