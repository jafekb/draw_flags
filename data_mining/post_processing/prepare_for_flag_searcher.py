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

import torch
from sentence_transformers import SentenceTransformer

from backend.src.load_flags import load_all_flag_info

DATA_DIR = Path("/home/bjafek/personal/draw_flags/data/national_flags")
ROOT_DIR = Path("/home/bjafek/personal/draw_flags/data/national_flags/data")
DIR_BASE = "flag_searcher"
OUT_DIR_NAME = DATA_DIR / DIR_BASE
OUT_DIR_NAME.mkdir(exist_ok=True)

# TODO(bjafek) pull out this name of the model to a central config
MODEL = SentenceTransformer("clip-ViT-B-32")

image_list, flags = load_all_flag_info(root_dir=ROOT_DIR)

ENCODED_IMAGES = MODEL.encode(
    image_list,
    batch_size=128,
    convert_to_tensor=True,
    show_progress_bar=True,
)

out_name_pth = OUT_DIR_NAME / "embeddings.pt"
out_name_json = OUT_DIR_NAME / "flags.json"

flags.embeddings_filename = str(out_name_pth)


torch.save(ENCODED_IMAGES, out_name_pth)
flags.to_json(out_name_json)

print(f"Successfully saved everything you'll need to {OUT_DIR_NAME}")
