"""
Script to download flag images and generate CLIP embeddings.
"""

import json
import time
from pathlib import Path
from typing import List

import numpy as np
import requests

from backend.common.flag_cleanup import clean_flags
from backend.common.flag_data import Flag, FlagList


def download_flag_images(flags: List[Flag], output_dir: Path, rate_limit_seconds: float = 1.0):
    """
    Download all flag images with rate limiting.

    Args:
        flags: List of Flag objects
        output_dir: Directory to save images
        rate_limit_seconds: Seconds to wait between downloads
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(flags)} flag images...")
    print(f"Rate limit: {rate_limit_seconds} seconds between requests")

    successful = 0
    failed = 0
    skipped = 0

    for i, flag in enumerate(flags):
        # Create safe filename from flag name
        safe_name = "".join(c for c in flag.name if c.isalnum() or c in (" ", "-", "_")).strip()
        safe_name = safe_name.replace(" ", "_")

        # Determine file extension from URL
        url_lower = flag.wikipedia_image_url.lower()
        if url_lower.endswith(".svg"):
            ext = ".svg"
        elif url_lower.endswith(".png"):
            ext = ".png"
        elif url_lower.endswith((".jpg", ".jpeg")):
            ext = ".jpg"
        elif url_lower.endswith(".gif"):
            ext = ".gif"
        else:
            # Default to PNG
            ext = ".png"

        output_file = output_dir / f"{safe_name}{ext}"

        # Skip if already downloaded
        if output_file.exists():
            skipped += 1
            if (i + 1) % 100 == 0:
                progress_message = (
                    f"  Progress: {i + 1}/{len(flags)} (successful: {successful}, "
                    f"failed: {failed}, skipped: {skipped})"
                )
                print(progress_message)
            continue

        # Download with retry logic
        max_retries = 3
        success = False

        for attempt in range(max_retries):
            try:
                time.sleep(rate_limit_seconds)

                response = requests.get(
                    flag.wikipedia_image_url,
                    timeout=30,
                    headers={
                        "User-Agent": (
                            "DrawFlags/1.0 (https://github.com/jafekb/draw_flags/; "
                            "jafek91@gmail.com)"
                        )
                    },
                )
                response.raise_for_status()

                with output_file.open("wb") as f:
                    f.write(response.content)

                successful += 1
                success = True
                break

            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"  Failed to download {flag.name}: {e}")
                    failed += 1
                else:
                    time.sleep(2**attempt)  # Exponential backoff

        if not success:
            continue

        # Progress update
        if (i + 1) % 100 == 0:
            progress_message = (
                f"  Progress: {i + 1}/{len(flags)} (successful: {successful}, "
                f"failed: {failed}, skipped: {skipped})"
            )
            print(progress_message)

    print("\nDownload complete:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Skipped (already existed): {skipped}")
    print(f"  Total: {len(flags)}")


def convert_svgs_to_png(images_dir: Path):
    """
    Convert SVG files to PNG for embedding generation.
    Requires cairosvg library.

    Args:
        images_dir: Directory containing images
    """
    try:
        import cairosvg
    except ImportError:
        print("cairosvg not available, skipping SVG conversion")
        print("Install with: pip install cairosvg")
        return

    svg_files = list(images_dir.glob("*.svg"))
    print(f"\nConverting {len(svg_files)} SVG files to PNG...")

    for svg_file in svg_files:
        png_file = svg_file.with_suffix(".png")

        if png_file.exists():
            continue

        try:
            with svg_file.open("r") as f:
                svg_data = f.read()
            cairosvg.svg2png(bytestring=svg_data.encode("utf-8"), write_to=str(png_file))
            print(f"  Converted: {svg_file.name}")
        except Exception as e:
            print(f"  Failed to convert {svg_file.name}: {e}")

    print("SVG conversion complete")


def generate_embeddings(flags: List[Flag], images_dir: Path, output_file: Path):
    """
    Generate CLIP embeddings for all flag images.

    Args:
        flags: List of Flag objects
        images_dir: Directory containing downloaded images
        output_file: Output file for embeddings (.npy)
    """
    print(f"\nGenerating CLIP embeddings for {len(flags)} flags...")

    try:
        from PIL import Image as PILImage
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(f"Required libraries not available: {e}")
        print("Install with: uv pip install sentence-transformers pillow")
        # Create dummy embeddings file so the script can continue
        print("Creating placeholder embeddings file...")
        np.save(output_file, np.zeros((len(flags), 512)))
        return

    # Load CLIP model
    print("Loading CLIP model...")
    model = SentenceTransformer("clip-ViT-B-32")

    embeddings = []
    successful = 0
    failed = 0

    for i, flag in enumerate(flags):
        # Find image file
        safe_name = "".join(c for c in flag.name if c.isalnum() or c in (" ", "-", "_")).strip()
        safe_name = safe_name.replace(" ", "_")

        # Try different extensions
        image_file = None
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg"]:
            candidate = images_dir / f"{safe_name}{ext}"
            if candidate.exists():
                image_file = candidate
                break

        if not image_file:
            print(f"  Image not found for: {flag.name}")
            # Use zero embedding as placeholder
            embeddings.append(np.zeros(512))
            failed += 1
            continue

        try:
            # Load and encode image
            image = PILImage.open(image_file).convert("RGB")
            embedding = model.encode(image, convert_to_numpy=True)
            embeddings.append(embedding)
            successful += 1

            if (i + 1) % 100 == 0:
                print(
                    f"  Progress: {i + 1}/{len(flags)} (successful: {successful}, failed: {failed})"
                )

        except Exception as e:
            print(f"  Failed to encode {flag.name}: {e}")
            embeddings.append(np.zeros(512))
            failed += 1

    # Convert to numpy array and save
    embeddings_array = np.array(embeddings)
    np.save(output_file, embeddings_array)

    print("\nEmbedding generation complete:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(flags)}")
    print(f"  Saved to: {output_file}")


def create_final_dataset(flags: List[Flag], embeddings_file: Path, output_dir: Path):
    """
    Create the final flags.json with embeddings reference.

    Args:
        flags: List of Flag objects
        embeddings_file: Path to embeddings file
        output_dir: Output directory
    """
    flag_list = FlagList(flags=flags, embeddings_filename=str(embeddings_file))

    output_file = output_dir / "flags.json"
    flag_list.to_json(output_file)

    print(f"\nCreated final dataset: {output_file}")
    print(f"  Total flags: {len(flags)}")
    print(f"  Embeddings: {embeddings_file}")


def main():
    """Main processing function."""
    # Load deduplicated flags
    flags_file = Path("backend/data/all_flags/flags_deduplicated.json")

    if not flags_file.exists():
        print(f"Error: {flags_file} not found")
        print("Please run collect_all_flags.py first")
        return

    print(f"Loading flags from {flags_file}...")
    with flags_file.open() as f:
        data = json.load(f)

    flags = [Flag(**flag_data) for flag_data in data]
    flags = clean_flags(flags, validate_wikipedia=True)
    print(f"Loaded {len(flags)} flags")

    # Setup paths
    output_dir = Path("backend/data/all_flags")
    images_dir = output_dir / "images"
    embeddings_file = output_dir / "embeddings.npy"

    # Step 1: Download images
    print("\n" + "=" * 80)
    print("STEP 1: Downloading flag images")
    print("=" * 80)
    download_flag_images(flags, images_dir, rate_limit_seconds=1.0)

    # Step 2: Convert SVGs to PNG
    print("\n" + "=" * 80)
    print("STEP 2: Converting SVG files to PNG")
    print("=" * 80)
    convert_svgs_to_png(images_dir)

    # Step 3: Generate embeddings
    print("\n" + "=" * 80)
    print("STEP 3: Generating CLIP embeddings")
    print("=" * 80)
    generate_embeddings(flags, images_dir, embeddings_file)

    # Step 4: Create final dataset
    print("\n" + "=" * 80)
    print("STEP 4: Creating final dataset")
    print("=" * 80)
    create_final_dataset(flags, embeddings_file, output_dir)

    # Create sources.txt
    sources_file = output_dir / "sources.txt"
    with sources_file.open("w") as f:
        f.write("Flag Database Sources\n")
        f.write("=" * 80 + "\n\n")
        f.write("This comprehensive flag database was compiled from the following sources:\n\n")
        f.write("1. Wikipedia (https://en.wikipedia.org)\n")
        f.write("   - National flags\n")
        f.write("   - Country subdivision flags (states, provinces, territories)\n")
        f.write("   - City and municipal flags\n")
        f.write("   - International organization flags\n")
        f.write("   - Historical flags\n\n")
        f.write("2. Flags of the World (FOTW) (https://www.crwflags.com/fotw/flags/)\n")
        f.write("   - Military flags\n")
        f.write("   - Naval ensigns\n")
        f.write("   - Political flags\n")
        f.write("   - Sports flags\n\n")
        f.write("All flag images are used under their respective licenses.\n")
        f.write("Please refer to the original sources for licensing information.\n\n")
        f.write("Created by DrawFlags project (https://github.com/jafekb/draw_flags/)\n")

    print(f"\nCreated sources attribution: {sources_file}")

    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)
    print(f"\nFinal dataset location: {output_dir}")
    print("To use this dataset, update backend/src/flag_searcher.py:")
    print("  FLAGS_FILE = Path('backend/data/all_flags/flags.json')")


if __name__ == "__main__":
    main()
