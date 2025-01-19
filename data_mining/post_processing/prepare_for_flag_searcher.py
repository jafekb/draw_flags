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
from PIL import Image
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from common.flag_data import FlagList, flag_from_json

# DATA_DIR = Path("/home/bjafek/personal/draw_flags/data/national_flags")
# ROOT_DIR = Path("/home/bjafek/personal/draw_flags/data/national_flags/data")
DATA_DIR = Path("/home/bjafek/personal/draw_flags/data/commons_plus_national")
ROOT_DIR = Path("/home/bjafek/personal/draw_flags/data/commons_plus_national/data")
DIR_BASE = "flag_searcher"
OUT_DIR_NAME = DATA_DIR / DIR_BASE
OUT_DIR_NAME.mkdir(exist_ok=True)

# TODO(bjafek) pull out this name of the model to a central config
MODEL = SentenceTransformer("clip-ViT-B-32")

jsons = list(ROOT_DIR.rglob("*.json"))
n_jsons = len(jsons)
flags = []
encodings = []
for idx, fn in tqdm(enumerate(jsons), total=n_jsons):
    flag = flag_from_json(fn)

    flags.append(flag)

    # TODO(bjafek) it's way slow to do it this way, you should
    #  at least chunk it.
    try:
        img = Image.open(flag.local_image_link)
    except:  # noqa: E722
        print(f"Skipping {fn}")
        continue
    single_image_encodings = MODEL.encode([img])
    encodings.append(single_image_encodings.ravel())
    img.close()

ENCODED_IMAGES = torch.tensor(encodings)
print(ENCODED_IMAGES.shape)
flag_list = FlagList(flags=flags)
out_name_pth = OUT_DIR_NAME / "embeddings.pt"
out_name_json = OUT_DIR_NAME / "flags.json"

flag_list.embeddings_filename = str(out_name_pth)


torch.save(ENCODED_IMAGES, out_name_pth)
flag_list.to_json(out_name_json)

print(f"Successfully saved everything you'll need to {OUT_DIR_NAME}")
