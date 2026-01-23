from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from add_color_metadata import COLOR_PALETTE, rgb_to_lab
from PIL import Image

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}


def parse_args() -> argparse.Namespace:
    default_images_dir = Path(__file__).resolve().parents[1] / "data" / "colors"
    parser = argparse.ArgumentParser(
        description="Visualize color pixels and palette centroids in CIELAB space.",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=default_images_dir,
        help="Root directory containing color images.",
    )
    parser.add_argument(
        "--sample-per-image",
        type=int,
        default=2000,
        help="Number of pixels to sample per image.",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=None,
        help="Limit number of images processed (for faster iteration).",
    )
    parser.add_argument(
        "--max-dimension",
        type=int,
        default=256,
        help="Resize images so max(width, height) <= this value.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Random seed used for pixel sampling.",
    )
    return parser.parse_args()


def iter_image_paths(images_dir: Path) -> list[Path]:
    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    return sorted(
        path
        for path in images_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def resize_image(image: Image.Image, max_dimension: int) -> Image.Image:
    width, height = image.size
    if max(width, height) <= max_dimension:
        return image
    scale = max_dimension / max(width, height)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(new_size, Image.BILINEAR)


def sample_pixels(
    image_paths: list[Path],
    sample_per_image: int,
    max_dimension: int,
    max_images: int | None,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    sampled = []
    for idx, path in enumerate(image_paths):
        if max_images is not None and idx >= max_images:
            break
        with Image.open(path) as image:
            image = image.convert("RGB")
            image = resize_image(image, max_dimension=max_dimension)
            pixels = np.asarray(image, dtype=np.uint8).reshape(-1, 3)
        if pixels.size == 0:
            continue
        if pixels.shape[0] > sample_per_image:
            indices = rng.choice(pixels.shape[0], sample_per_image, replace=False)
            pixels = pixels[indices]
        sampled.append(pixels)
    if not sampled:
        raise ValueError("No pixels were sampled from the provided images.")
    return np.vstack(sampled)


def plot_lab_colors(rgb_samples: np.ndarray) -> None:
    lab_samples = rgb_to_lab(rgb_samples.astype(np.float32))
    colors = rgb_samples.astype(np.float32) / 255.0

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(
        lab_samples[:, 1],
        lab_samples[:, 2],
        lab_samples[:, 0],
        c=colors,
        s=6,
        alpha=0.6,
        linewidths=0,
    )

    palette_names = list(COLOR_PALETTE.keys())
    palette_rgb = np.array(list(COLOR_PALETTE.values()), dtype=np.float32)
    palette_lab = rgb_to_lab(palette_rgb)
    palette_colors = palette_rgb / 255.0

    ax.scatter(
        palette_lab[:, 1],
        palette_lab[:, 2],
        palette_lab[:, 0],
        c=palette_colors,
        s=160,
        edgecolors="black",
        linewidths=0.6,
    )

    for name, (a_val, b_val, l_val) in zip(
        palette_names,
        np.column_stack((palette_lab[:, 1], palette_lab[:, 2], palette_lab[:, 0])),
    ):
        ax.text(a_val, b_val, l_val, name, fontsize=9)

    ax.set_xlabel("a*")
    ax.set_ylabel("b*")
    ax.set_zlabel("L*")
    ax.set_title("CIELAB Color Distribution with Palette Centroids")
    plt.tight_layout()
    plt.show()


def main() -> None:
    args = parse_args()
    image_paths = iter_image_paths(args.images_dir)
    rgb_samples = sample_pixels(
        image_paths=image_paths,
        sample_per_image=args.sample_per_image,
        max_dimension=args.max_dimension,
        max_images=args.max_images,
        seed=args.seed,
    )
    plot_lab_colors(rgb_samples)


if __name__ == "__main__":
    main()
