#!/usr/bin/python
"""
Process all the files that we downloaded.
"""

import json
import logging
from pathlib import Path

# import coloredlogs
from tqdm import tqdm
from utils import check_options

# coloredlogs.install()

# TODO(bjafek) make a constants.py instead of re-defining here.
DATA_DIR = Path("/home/bjafek/personal/draw_flags/data_mining/wikimedia-downloader/output")
POST_DIR = Path("/home/bjafek/personal/draw_flags/data_mining/wikimedia-downloader/post_processed")
POST_DIR.mkdir(exist_ok=True)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(
            "/home/bjafek/personal/draw_flags/data_mining/post_processing/filename.log"
        ),
    ],
)


data = sorted(DATA_DIR.rglob("*.json"))
n_files = len(data)

for idx, path in tqdm(enumerate(data), total=n_files):
    post_process_name = POST_DIR / path.relative_to(DATA_DIR)
    if post_process_name.is_file():
        continue

    with path.open() as f:
        single_row = json.load(f)

    single_row["verified_page"] = None
    single_row["verified_url"] = None

    # TODO(bjafek) this is actually a lot more useful avenue -
    #  It works for every one, and the page has a 'File Usage' section
    url_base = single_row["image_url"].split("/")[-1]
    single_row["commons_link"] = f"https://en.m.wikipedia.org/wiki/File:{url_base}"

    single_row = check_options(single_row, idx)

    post_process_name.parent.mkdir(exist_ok=True, parents=True)
    with post_process_name.open("w") as f:
        json.dump(single_row, f, indent=1)
