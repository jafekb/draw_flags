from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from add_color_metadata import COLOR_PALETTE, lab_distances, palette_lab, rgb_to_lab
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
    return parser.parse_args()


def resize_image(image: Image.Image, max_dimension: int) -> Image.Image:
    width, height = image.size
    if max(width, height) <= max_dimension:
        return image
    scale = max_dimension / max(width, height)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(new_size, Image.BILINEAR)


def palette_arrays() -> tuple[list[str], np.ndarray, np.ndarray]:
    names, lab = palette_lab()
    rgb = np.array([COLOR_PALETTE[name] for name in names], dtype=np.float32)
    return names, rgb, lab


def map_pixels_to_palette(
    rgba: np.ndarray,
    palette_rgb: np.ndarray,
    palette_lab: np.ndarray,
) -> np.ndarray:
    alpha = rgba[:, 3:4]
    rgb = rgba[:, :3]
    lab = rgb_to_lab(rgb)
    distances = lab_distances(lab, palette_lab)
    indices = np.argmin(distances, axis=1)
    mapped_rgb = palette_rgb[indices].astype(np.uint8)
    return np.concatenate([mapped_rgb, alpha], axis=1)


def main() -> None:
    args = parse_args()
    images_dir = args.images_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    Image.MAX_IMAGE_PIXELS = None

    _, palette_rgb, palette_lab = palette_arrays()
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
            mapped = map_pixels_to_palette(sampled, palette_rgb, palette_lab)
            mapped_full = rgba.copy()
            mapped_full[indices] = mapped
            mapped_rgba = mapped_full
        else:
            mapped_rgba = map_pixels_to_palette(rgba, palette_rgb, palette_lab)

        mapped_image = Image.fromarray(mapped_rgba.reshape(image.size[1], image.size[0], 4))
        combined = Image.new("RGBA", (image.width * 2, image.height))
        combined.paste(image, (0, 0))
        combined.paste(mapped_image, (image.width, 0))

        output_path = output_dir / f"{path.stem}_palette.png"
        combined.save(output_path)


if __name__ == "__main__":
    main()
