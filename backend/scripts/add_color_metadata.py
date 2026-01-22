from __future__ import annotations

import argparse
import io
import json
import random
from pathlib import Path

import cairosvg
import numpy as np
import requests
from PIL import Image

COLOR_PALETTE = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "gray": (128, 128, 128),
    "red": (154, 45, 61),
    "orange": (226, 111, 45),
    "yellow": (255, 215, 0),
    "green": (0, 128, 0),
    "blue": (33, 74, 143),
    "light_blue": (135, 206, 235),
    "purple": (136, 41, 109),
    "pink": (221, 100, 144),
}

MIN_SATURATION = 0.33620688
MIN_VALUE = 0.4627451

WIKIMEDIA_HEADERS = {
    "User-Agent": "DrawFlags/0.0 (https://github.com/jafekb/draw_flags/; jafek91@gmail.com)"
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add color coverage metadata to flags.json",
    )
    parser.add_argument(
        "--flags-json",
        type=Path,
        required=True,
        help="Path to flags.json to update",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (defaults to overwrite input)",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=None,
        help="Optional local images directory to load instead of downloading",
    )
    parser.add_argument(
        "--max-dimension",
        type=int,
        default=256,
        help="Max width/height to resize images for faster processing",
    )
    parser.add_argument(
        "--sample-max",
        type=int,
        default=50000,
        help="Max pixels sampled per image",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute even if color_coverage already exists",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process first N flags (debug)",
    )
    return parser.parse_args()


def fetch_image(url: str) -> Image.Image:
    Image.MAX_IMAGE_PIXELS = None
    response = requests.get(url, headers=WIKIMEDIA_HEADERS, timeout=30)
    response.raise_for_status()
    content = response.content

    suffix = url.split(".")[-1].lower()
    if suffix == "svg":
        png_bytes = cairosvg.svg2png(bytestring=content, unsafe=True)
        return Image.open(io.BytesIO(png_bytes))
    return Image.open(io.BytesIO(content))


def safe_image_name(name: str) -> str:
    safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()
    return safe_name.replace(" ", "_")


def load_local_image(images_dir: Path, flag_name: str) -> Image.Image | None:
    Image.MAX_IMAGE_PIXELS = None
    safe_name = safe_image_name(flag_name)
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".svg"):
        candidate = images_dir / f"{safe_name}{ext}"
        if not candidate.exists():
            continue
        if candidate.suffix.lower() == ".svg":
            svg_bytes = candidate.read_bytes()
            png_bytes = cairosvg.svg2png(bytestring=svg_bytes, unsafe=True)
            return Image.open(io.BytesIO(png_bytes))
        return Image.open(candidate)
    return None


def resize_image(image: Image.Image, max_dimension: int) -> Image.Image:
    width, height = image.size
    if max(width, height) <= max_dimension:
        return image
    scale = max_dimension / max(width, height)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(new_size, Image.BILINEAR)


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb / 255.0
    mask = rgb <= 0.04045
    linear = np.where(mask, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return linear


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    linear = srgb_to_linear(rgb.astype(np.float32))
    matrix = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ],
        dtype=np.float32,
    )
    xyz = linear @ matrix.T
    xyz_ref = np.array([0.95047, 1.0, 1.08883], dtype=np.float32)
    xyz = xyz / xyz_ref
    delta = 6 / 29
    delta3 = delta**3
    f = np.where(xyz > delta3, xyz ** (1 / 3), (xyz / (3 * delta**2)) + (4 / 29))
    l_val = (116 * f[:, 1]) - 16
    a_val = 500 * (f[:, 0] - f[:, 1])
    b_val = 200 * (f[:, 1] - f[:, 2])
    return np.stack([l_val, a_val, b_val], axis=1)


def rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb.astype(np.float32) / 255.0
    c_max = np.max(rgb, axis=1)
    c_min = np.min(rgb, axis=1)
    delta = c_max - c_min

    hue = np.zeros_like(c_max)
    nonzero = delta > 0
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]

    red_mask = nonzero & (c_max == r)
    green_mask = nonzero & (c_max == g)
    blue_mask = nonzero & (c_max == b)

    hue[red_mask] = (60 * ((g[red_mask] - b[red_mask]) / delta[red_mask])) % 360
    hue[green_mask] = 60 * ((b[green_mask] - r[green_mask]) / delta[green_mask] + 2)
    hue[blue_mask] = 60 * ((r[blue_mask] - g[blue_mask]) / delta[blue_mask] + 4)

    saturation = np.zeros_like(c_max)
    nonzero_value = c_max > 0
    saturation[nonzero_value] = delta[nonzero_value] / c_max[nonzero_value]

    value = c_max
    return np.stack([hue, saturation, value], axis=1)


def palette_lab() -> tuple[list[str], np.ndarray]:
    names = list(COLOR_PALETTE.keys())
    rgb = np.array([COLOR_PALETTE[name] for name in names], dtype=np.float32)
    return names, rgb_to_lab(rgb)


def nearest_palette_indices(
    pixels_lab: np.ndarray,
    palette: np.ndarray,
    blocked_indices: np.ndarray | None = None,
    blocked_mask: np.ndarray | None = None,
) -> np.ndarray:
    diffs = pixels_lab[:, None, :] - palette[None, :, :]
    distances = np.sum(diffs * diffs, axis=2)
    if blocked_indices is not None and blocked_mask is not None and blocked_mask.any():
        distances[blocked_mask[:, None], blocked_indices] = np.inf
    return np.argmin(distances, axis=1)


def compute_color_coverage(
    image: Image.Image,
    palette_names: list[str],
    palette_lab_values: np.ndarray,
    sample_max: int,
) -> dict[str, float]:
    image = image.convert("RGBA")
    pixels = np.array(image).reshape(-1, 4)
    opaque = pixels[:, 3] > 0
    rgb = pixels[opaque, :3]
    if rgb.size == 0:
        return {}

    if rgb.shape[0] > sample_max:
        indices = random.sample(range(rgb.shape[0]), sample_max)
        rgb = rgb[indices]

    lab = rgb_to_lab(rgb)
    hsv = rgb_to_hsv(rgb)
    guardrail_mask = (hsv[:, 1] < MIN_SATURATION) | (hsv[:, 2] < MIN_VALUE)
    protected = np.array(
        [palette_names.index(name) for name in ("red", "pink", "purple")],
        dtype=np.int64,
    )
    palette_indices = nearest_palette_indices(
        lab,
        palette_lab_values,
        blocked_indices=protected,
        blocked_mask=guardrail_mask,
    )
    counts = np.bincount(palette_indices, minlength=len(palette_names))

    total = counts.sum()
    if total == 0:
        return {}

    coverage = counts.astype(np.float32) / float(total)
    return {
        palette_names[i]: float(coverage[i]) for i in range(len(palette_names)) if counts[i] > 0
    }


def main() -> None:
    args = parse_args()
    flags_path = args.flags_json
    output_path = args.output or flags_path
    images_dir = args.images_dir

    if not flags_path.is_file():
        raise FileNotFoundError(flags_path)

    with flags_path.open() as f:
        data = json.load(f)

    flags = data.get("flags", [])
    names, palette_values = palette_lab()
    if images_dir is None:
        candidate = flags_path.parent / "images"
        images_dir = candidate if candidate.is_dir() else None

    processed = 0
    for flag in flags:
        if args.limit is not None and processed >= args.limit:
            break
        if not args.force and flag.get("color_coverage"):
            processed += 1
            continue

        image_url = flag.get("wikipedia_image_url")
        if not image_url:
            processed += 1
            continue

        try:
            image = None
            if images_dir is not None:
                image = load_local_image(images_dir, flag.get("name", ""))
            if image is None:
                image = fetch_image(image_url)
            image = resize_image(image, args.max_dimension)
            coverage = compute_color_coverage(
                image=image,
                palette_names=names,
                palette_lab_values=palette_values,
                sample_max=args.sample_max,
            )
            flag["color_coverage"] = coverage
        except Exception as exc:
            print(f"Failed to process {flag.get('name', 'unknown')}: {exc}")
        processed += 1

    data["flags"] = flags
    with output_path.open("w") as f:
        json.dump(data, f, indent=1)


if __name__ == "__main__":
    main()
