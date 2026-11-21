#!/usr/bin/env python3
"""
Generate CLIP embeddings from an existing flags.json and images directory.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

import numpy as np

from backend.common.flag_data import Flag, flaglist_from_json
from backend.src.vector_index import HnswIndex

SKIP_IMAGE_NAMES = {"Paris_variant_2.svg"}


def _safe_name(name: str) -> str:
    safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()
    return safe_name.replace(" ", "_")


def _find_image_file(images_dir: Path, flag_name: str, extensions: Iterable[str]) -> Path | None:
    safe_name = _safe_name(flag_name)
    for ext in extensions:
        candidate = images_dir / f"{safe_name}{ext}"
        if candidate.name in SKIP_IMAGE_NAMES:
            continue
        if candidate.exists():
            return candidate
    return None


def _load_clip_model():
    try:
        from PIL import Image as PILImage
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Required libraries not available. "
            "Install with: uv pip install sentence-transformers pillow"
        ) from exc
    return SentenceTransformer("clip-ViT-B-32"), PILImage


def convert_svgs_to_png(images_dir: Path, failures: List[str]) -> None:
    try:
        import cairosvg
    except ImportError:
        failures.append("SVG conversion skipped: cairosvg not installed.")
        print("cairosvg not available, skipping SVG conversion")
        return

    svg_files = list(images_dir.glob("*.svg"))
    if not svg_files:
        return

    print(f"\nConverting {len(svg_files)} SVG files to PNG...")
    for svg_file in svg_files:
        if svg_file.name in SKIP_IMAGE_NAMES:
            continue
        png_file = svg_file.with_suffix(".png")
        if png_file.exists():
            continue

        try:
            svg_data = svg_file.read_text()
            cairosvg.svg2png(bytestring=svg_data.encode("utf-8"), write_to=str(png_file))
        except Exception as exc:
            failures.append(f"SVG conversion failed for {svg_file.name}: {exc}")
    print("SVG conversion complete")


def generate_embeddings(
    flags: List[Flag], images_dir: Path, output_file: Path, failures: List[str]
) -> np.ndarray:
    print(f"\nGenerating CLIP embeddings for {len(flags)} flags...")

    try:
        model, pil_image = _load_clip_model()
    except RuntimeError as exc:
        print(str(exc))
        print("Creating placeholder embeddings file...")
        embeddings_array = np.zeros((len(flags), 512), dtype=np.float32)
        np.save(output_file, embeddings_array)
        failures.append("Embedding generation fell back to placeholders due to missing deps.")
        return embeddings_array

    embeddings: List[np.ndarray] = []
    successful = 0
    failed = 0
    extensions = [".png", ".jpg", ".jpeg", ".gif", ".svg"]
    progress_file = Path("/tmp/embedding_progress.txt")
    progress_file.write_text("Starting embedding generation...\n")

    for i, flag in enumerate(flags):
        progress_file.write_text(f"Embedding {i + 1} of {len(flags)} ({flag.name})\n")
        image_file = _find_image_file(images_dir, flag.name, extensions)
        if not image_file:
            message = f"Image not found for: {flag.name}"
            print(f"  {message}")
            failures.append(message)
            embeddings.append(np.zeros(512, dtype=np.float32))
            failed += 1
            continue

        try:
            image = pil_image.open(image_file).convert("RGB")
            embedding = model.encode(image, convert_to_numpy=True)
            embeddings.append(embedding.astype(np.float32))
            successful += 1
            if (i + 1) % 100 == 0:
                print(
                    f"  Progress: {i + 1}/{len(flags)} (successful: {successful}, failed: {failed})"
                )
        except Exception as exc:
            message = f"Failed to encode {flag.name}: {exc}"
            print(f"  {message}")
            failures.append(message)
            embeddings.append(np.zeros(512, dtype=np.float32))
            failed += 1

        if (i + 1) % 50 == 0:
            np.save(output_file, np.asarray(embeddings, dtype=np.float32))

    embeddings_array = np.asarray(embeddings, dtype=np.float32)
    np.save(output_file, embeddings_array)

    print("\nEmbedding generation complete:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(flags)}")
    print(f"  Saved to: {output_file}")

    return embeddings_array


def _maybe_remove_index(embeddings_path: Path) -> None:
    index_path = embeddings_path.with_suffix(".hnsw.bin")
    meta_path = embeddings_path.with_suffix(".hnsw.meta.json")
    for path in (index_path, meta_path):
        if path.exists():
            path.unlink()


def build_hnsw_index(embeddings: np.ndarray, embeddings_path: Path, *, rebuild_index: bool) -> None:
    index_path = embeddings_path.with_suffix(".hnsw.bin")
    meta_path = embeddings_path.with_suffix(".hnsw.meta.json")
    if rebuild_index:
        _maybe_remove_index(embeddings_path)
    elif index_path.exists() and meta_path.exists():
        embeddings_mtime = embeddings_path.stat().st_mtime
        if (
            index_path.stat().st_mtime < embeddings_mtime
            or meta_path.stat().st_mtime < embeddings_mtime
        ):
            _maybe_remove_index(embeddings_path)

    HnswIndex.load_or_build(embeddings, index_path, meta_path)
    print(f"Created HNSW index: {index_path}")
    print(f"Created HNSW metadata: {meta_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate embeddings from flags.json and an images directory."
    )
    parser.add_argument(
        "--flags-json",
        default="backend/data/all_flags/flags.json",
        help="Path to flags.json",
    )
    parser.add_argument(
        "--images-dir",
        default="backend/data/all_flags/images",
        help="Directory containing flag images",
    )
    parser.add_argument(
        "--output-embeddings",
        default="backend/data/all_flags/embeddings.npy",
        help="Output embeddings .npy path",
    )
    parser.add_argument(
        "--convert-svgs",
        action="store_true",
        help="Convert SVGs to PNGs before embedding generation",
    )
    parser.add_argument(
        "--failure-log",
        default="backend/data/all_flags/embedding_failures.log",
        help="Path to write embedding/conversion failures",
    )
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Force rebuild of the HNSW index even if it exists",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    flags_json = Path(args.flags_json)
    images_dir = Path(args.images_dir)
    output_embeddings = Path(args.output_embeddings)
    failure_log = Path(args.failure_log)

    if not flags_json.exists():
        raise FileNotFoundError(f"flags.json not found at {flags_json}")
    if not images_dir.exists():
        raise FileNotFoundError(f"images directory not found at {images_dir}")

    flag_list = flaglist_from_json(flags_json)
    flags = flag_list.flags
    print(f"Loaded {len(flags)} flags from {flags_json}")

    output_embeddings.parent.mkdir(parents=True, exist_ok=True)
    failures: List[str] = []

    if args.convert_svgs:
        convert_svgs_to_png(images_dir, failures)

    embeddings = generate_embeddings(flags, images_dir, output_embeddings, failures)
    build_hnsw_index(embeddings, output_embeddings, rebuild_index=args.rebuild_index)

    if failures:
        failure_log.parent.mkdir(parents=True, exist_ok=True)
        failure_log.write_text("\n".join(failures) + "\n")
        print(f"\nWrote failures to: {failure_log}")

    print("\nPROCESSING COMPLETE")
    print(f"Embeddings saved to: {output_embeddings}")


if __name__ == "__main__":
    main()
