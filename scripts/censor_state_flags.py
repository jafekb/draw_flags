#!/usr/bin/env python3
"""
Fine-grained one-time text-censoring pipeline for jafekb/draw_flags:
1. Filters legacy/backend/data/all_flags/flags.json to National + US States + Canadian Provinces.
2. Strips literal <text> / <tspan> nodes from downloaded SVGs first (zero false positives).
3. Rasterizes to PNG and runs EasyOCR (handles curved/rotated seal text like Kentucky)
   with tight polygon masking filled using the local sampled background color.
4. Saves compact .webp images (~15-30 KB each) to frontend/public/flags_censored/
   and writes frontend/public/active_flags.json.
"""

import io
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

# import cairosvg
import resvg_py
import easyocr
import numpy as np
import requests
from PIL import Image, ImageDraw
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
SRC_JSON = ROOT / "legacy" / "backend" / "data" / "all_flags" / "flags.json"
OUT_JSON = ROOT / "frontend" / "public" / "active_flags.json"
CENSOR_DIR = ROOT / "frontend" / "public" / "flags_censored"

US_STATES = {
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
    "District of Columbia",
    "Washington, D.C.",
}

CA_PROVINCES = {
    "Alberta",
    "British Columbia",
    "Manitoba",
    "New Brunswick",
    "Newfoundland and Labrador",
    "Nova Scotia",
    "Ontario",
    "Prince Edward Island",
    "Quebec",
    "Saskatchewan",
    "Northwest Territories",
    "Nunavut",
    "Yukon",
}

HEADERS = {"User-Agent": "WhatsThatFlagQuizBot/1.0 (https://whatsthatflag.com)"}

VARIANT_RE = re.compile(
    r"\b(variant|ensign|standard|civil|naval|air\s+force|army|merchant|government|vertical|reverse|obverse|unofficial|proposed|alternative|construction|ratio)\b",
    re.IGNORECASE,
)


def classify_group(flag: dict):
    name = (flag.get("name") or "").strip()
    cat = (flag.get("category") or "").lower()
    et = (flag.get("entity_type") or "").lower()

    if re.search(r"\(\d{3,4}|1[0-9]{3}|20[0-2][0-9]", name) or cat == "historical":
        return None
    if VARIANT_RE.search(name) or VARIANT_RE.search(et) or VARIANT_RE.search(cat):
        return None
    if name in US_STATES and (cat == "subdivision" or et == "state"):
        if name == "Georgia" and cat == "national":
            return "national"
        return "us_state"
    if name in CA_PROVINCES:
        return "ca_province"
    if cat == "national":
        return "national"
    return None


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def strip_svg_text_nodes(svg_bytes: bytes) -> tuple[bytes, bool]:
    """Remove literal <text> and <tspan> elements from SVG XML before rasterizing."""
    stripped = False
    try:
        root = ET.fromstring(svg_bytes)
        for parent in root.iter():
            for child in list(parent):
                tag = child.tag.split("}")[-1].lower()
                if tag in ("text", "tspan", "textpath"):
                    parent.remove(child)
                    stripped = True
        return ET.tostring(root, encoding="utf-8"), stripped
    except Exception:
        return svg_bytes, False


def sample_border_color(arr: np.ndarray, pts: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0 = max(0, min(xs) - 3)
    y0 = max(0, min(ys) - 3)
    x1 = min(arr.shape[1] - 1, max(xs) + 3)
    y1 = min(arr.shape[0] - 1, max(ys) + 3)
    patch = arr[y0 : y1 + 1, x0 : x1 + 1, :3]
    if patch.size == 0:
        return (24, 24, 27, 255)
    med = np.median(patch.reshape(-1, 3), axis=0).astype(int)
    return (int(med[0]), int(med[1]), int(med[2]), 255)


def censor_flag_image(url: str, out_path: Path, reader: easyocr.Reader) -> bool:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    cleaned_svg, stripped_xml = strip_svg_text_nodes(resp.content)
    # png_bytes = cairosvg.svg2png(bytestring=cleaned_svg, output_width=640)
    png_bytes = resvg_py.svg_to_bytes(
        svg_string=cleaned_svg.decode("utf-8"),
        width=640,
    )
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    arr = np.array(img)

    # EasyOCR detects angled & curved text polygons cleanly
    results = reader.readtext(arr[:, :, :3], detail=1, paragraph=False)
    draw = ImageDraw.Draw(img)
    masked_ocr = False

    for bbox, text, conf in results:
        letters = re.sub(r"[^A-Za-z]", "", text or "")
        if len(letters) >= 2 and conf >= 0.25:
            pts = [(int(round(p[0])), int(round(p[1]))) for p in bbox]
            fill = sample_border_color(arr, pts)
            draw.polygon(pts, fill=fill)
            masked_ocr = True

    if stripped_xml or masked_ocr:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, format="WEBP", quality=82, method=6)
        return True
    return False


def main():
    if not SRC_JSON.exists():
        raise FileNotFoundError(
            f"Could not find {SRC_JSON}. Move backend/ into legacy/backend/ first."
        )

    reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    raw = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    flags = raw.get("flags", [])

    seen = set()
    active = []
    for f in tqdm(flags):
        group = classify_group(f)
        if not group or not f.get("wikipedia_image_url"):
            continue
        key = (group, f["name"])
        if key in seen:
            continue
        seen.add(key)

        entry = dict(f)
        entry["group"] = group

        if group in ("us_state", "ca_province"):
            filename = f"{slugify(f['name'])}.webp"
            out_path = CENSOR_DIR / filename
            try:
                if censor_flag_image(f["wikipedia_image_url"], out_path, reader):
                    entry["censored_image_url"] = f"/flags_censored/{filename}"
                    print(f"Censored: {f['name']}")
                else:
                    print(f"Clean (no text): {f['name']}")
            except Exception as exc:
                print(f"Skipped {f['name']} ({exc})")

        active.append(entry)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"flags": active}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote {len(active)} active flags to {OUT_JSON}")


if __name__ == "__main__":
    main()
