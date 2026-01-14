#!/usr/bin/python
"""
Once you have a data dir that looks like this:
data/
    data/
        *.json
    images/
        *.png

Then you can call this script to do the rest of the preparations
to create the deployment file for FlagSearcher.
"""

from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from backend.common.flag_data import FlagList, flag_from_json, flaglist_from_json  # noqa: E402
from backend.scripts.download_and_process import download_flag_images  # noqa: E402

DATASET_DIR = PROJECT_ROOT / "backend" / "data" / "comprehensive_flags_3"
if not DATASET_DIR.joinpath("flags.json").is_file():
    raise FileNotFoundError(f"Dataset flags.json not found at {DATASET_DIR}")

OUT_DIR_NAME = DATASET_DIR
OUT_DIR_NAME.mkdir(exist_ok=True)
flags_list = flaglist_from_json(DATASET_DIR / "flags.json")
flags = flags_list.flags
IMAGES_DIR = DATASET_DIR / "images"
use_dataset_images = True

# TODO(bjafek) pull out this name of the model to a central config
MODEL = SentenceTransformer("clip-ViT-B-32")
EMBEDDING_DIM = 512

def find_image_file(flag_name: str, images_dir: Path) -> Path | None:
    safe_name = "".join(c for c in flag_name if c.isalnum() or c in (" ", "-", "_")).strip()
    safe_name = safe_name.replace(" ", "_")
    for ext in [".png", ".jpg", ".jpeg", ".gif"]:
        candidate = images_dir / f"{safe_name}{ext}"
        if candidate.exists():
            return candidate
    svg_candidate = images_dir / f"{safe_name}.svg"
    if svg_candidate.exists():
        png_candidate = images_dir / f"{safe_name}.png"
        if not png_candidate.exists():
            try:
                subprocess.run(
                    ["cairosvg", str(svg_candidate), "-o", str(png_candidate)],
                    check=True,
                    timeout=20,
                )
            except Exception:
                return None
        return png_candidate
    return None

if use_dataset_images:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    if not any(IMAGES_DIR.iterdir()):
        print("Downloading images for comprehensive_flags_3...")
        download_flag_images(flags, IMAGES_DIR, rate_limit_seconds=0.2)

encodings = []
successful = 0
failed = 0
for idx, flag in tqdm(enumerate(flags), total=len(flags)):
    # TODO(bjafek) it's way slow to do it this way, you should
    #  at least chunk it.
    try:
        if use_dataset_images:
            img_path = find_image_file(flag.name, IMAGES_DIR)
            if not img_path:
                print(f"Missing image for {flag.name}; using zero embedding")
                encodings.append(np.zeros(EMBEDDING_DIM))
                failed += 1
                continue
            img = Image.open(img_path)
        else:
            img = Image.open(flag.local_image_link)
    except Exception:  # noqa: E722
        print(f"Failed to load image for {flag.name}; using zero embedding")
        encodings.append(np.zeros(EMBEDDING_DIM))
        failed += 1
        continue

    single_image_encodings = MODEL.encode([img])
    encodings.append(single_image_encodings.ravel())
    img.close()
    successful += 1

ENCODED_IMAGES = np.array(encodings)
print(ENCODED_IMAGES.shape)
print(f"Embeddings generated: {successful} successful, {failed} failed")
flag_list = FlagList(flags=flags)
out_name_npy = OUT_DIR_NAME / "embeddings.npy"
out_name_json = OUT_DIR_NAME / "flags.json"

flag_list.embeddings_filename = str(out_name_npy)

np.save(out_name_npy, ENCODED_IMAGES)
flag_list.to_json(out_name_json)

print(f"Successfully saved everything you'll need to {OUT_DIR_NAME}")
