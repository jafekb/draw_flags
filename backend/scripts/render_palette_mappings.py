from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from add_color_metadata import (
    COLOR_PALETTE,
    MIN_SATURATION,
    MIN_VALUE,
    rgb_to_hsv,
    rgb_to_lab,
)
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render original images next to COLOR_PALETTE mappings",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        required=True,
        help="Directory containing source images",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to write side-by-side outputs",
    )
    parser.add_argument(
        "--max-dimension",
        type=int,
        default=256,
        help="Resize images to this max dimension for speed",
    )
    parser.add_argument(
        "--sample-max",
        type=int,
        default=None,
        help="Optional max pixels to sample (None disables sampling)",
    )
    parser.add_argument(
        "--use-guardrail",
        action="store_true",
        help="Apply saturation/value guardrail to red/pink/purple mapping",
    )
    return parser.parse_args()


def resize_image(image: Image.Image, max_dimension: int) -> Image.Image:
    width, height = image.size
    if max(width, height) <= max_dimension:
        return image
    scale = max_dimension / max(width, height)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(new_size, Image.BILINEAR)


def palette_arrays() -> tuple[list[str], np.ndarray, np.ndarray]:
    names = list(COLOR_PALETTE.keys())
    rgb = np.array([COLOR_PALETTE[name] for name in names], dtype=np.float32)
    lab = rgb_to_lab(rgb)
    return names, rgb, lab


def map_pixels_to_palette(
    rgba: np.ndarray,
    palette_names: list[str],
    palette_rgb: np.ndarray,
    palette_lab: np.ndarray,
    *,
    use_guardrail: bool,
) -> np.ndarray:
    alpha = rgba[:, 3:4]
    rgb = rgba[:, :3]
    lab = rgb_to_lab(rgb)
    diffs = lab[:, None, :] - palette_lab[None, :, :]
    distances = np.sum(diffs * diffs, axis=2)

    if use_guardrail:
        hsv = rgb_to_hsv(rgb)
        guardrail_mask = (hsv[:, 1] < MIN_SATURATION) | (hsv[:, 2] < MIN_VALUE)
        protected = np.array(
            [palette_names.index(name) for name in ("red", "pink", "purple")],
            dtype=np.int64,
        )
        distances[guardrail_mask][:, protected] = np.inf

    indices = np.argmin(distances, axis=1)
    mapped_rgb = palette_rgb[indices].astype(np.uint8)
    return np.concatenate([mapped_rgb, alpha], axis=1)


def main() -> None:
    args = parse_args()
    images_dir = args.images_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    Image.MAX_IMAGE_PIXELS = None

    palette_names, palette_rgb, palette_lab = palette_arrays()
    supported_ext = {".png", ".jpg", ".jpeg", ".gif"}

    for path in sorted(images_dir.iterdir()):
        if path.suffix.lower() not in supported_ext:
            continue
        try:
            image = Image.open(path).convert("RGBA")
        except (Image.DecompressionBombError, ValueError) as exc:
            print(f"Skipping image {path.name}: {exc}")
            continue
        image = resize_image(image, args.max_dimension)
        rgba = np.array(image).reshape(-1, 4)

        if args.sample_max and rgba.shape[0] > args.sample_max:
            indices = np.random.choice(rgba.shape[0], size=args.sample_max, replace=False)
            sampled = rgba[indices]
            mapped = map_pixels_to_palette(
                sampled,
                palette_names,
                palette_rgb,
                palette_lab,
                use_guardrail=args.use_guardrail,
            )
            mapped_full = rgba.copy()
            mapped_full[indices] = mapped
            mapped_rgba = mapped_full
        else:
            mapped_rgba = map_pixels_to_palette(
                rgba,
                palette_names,
                palette_rgb,
                palette_lab,
                use_guardrail=args.use_guardrail,
            )

        mapped_image = Image.fromarray(mapped_rgba.reshape(image.size[1], image.size[0], 4))
        combined = Image.new("RGBA", (image.width * 2, image.height))
        combined.paste(image, (0, 0))
        combined.paste(mapped_image, (image.width, 0))

        output_path = output_dir / f"{path.stem}_palette.png"
        combined.save(output_path)


if __name__ == "__main__":
    main()
