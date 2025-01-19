#!/usr/bin/python3
import json
from pathlib import Path
from urllib.parse import unquote

from tqdm import tqdm

from common.flag_data import Flag

DIR_NAME = Path(
    "/home/bjafek/personal/draw_flags/data_mining/wikimedia-downloader/commons_verified/data"
)
INCLUDE_UNVERIFIED = False

OUT_DIR = Path("/home/bjafek/personal/draw_flags/data/all_commons")
(OUT_DIR / "images").mkdir(exist_ok=True)
(OUT_DIR / "data").mkdir(exist_ok=True)

list_of_flags = []

fnames = sorted(DIR_NAME.rglob("*.json"))
for fn in tqdm(fnames):
    with fn.open() as f:
        data = json.load(f)

    verif_page = data["verified_page"]
    if verif_page is None and not INCLUDE_UNVERIFIED:
        continue

    name = Path(data["commons_link"]).stem.replace("File:", "").replace("_", " ")
    name = unquote(name)

    flag = Flag(
        name=name,
        wikipedia_page=data["verified_page"],
        wikipedia_url=data["verified_url"],
        wikipedia_image_url=data["image_url"],
        local_image_link=data["image_path"],
        verification_method=data["verification_method"],
        score=1.0,
    )
    local_link = Path(flag.local_image_link)
    if local_link.suffix in (".svg", ".SVG"):
        continue
    download = flag.save_image(OUT_DIR / "images")
    list_of_flags.append(flag)

    flag.to_json(OUT_DIR / "data")
    assert not download
