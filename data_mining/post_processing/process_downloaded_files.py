#!/usr/bin/python
"""
Process all the files that we downloaded.
"""

import json
import logging
from pathlib import Path

import coloredlogs
import wikipedia
from utils import methods_of_fixing

# TODO(bjafek) make a constants.py instead of re-defining here.
coloredlogs.install()

OUT_DIR = Path("/home/bjafek/personal/draw_flags/data_mining/wikimedia-downloader/output")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("filename.log"),
        logging.StreamHandler(),
    ],
)


data = sorted(OUT_DIR.rglob("*.json"))
n_files = len(data)

all_rows = []

# for idx, fn in tqdm(enumerate(data), total=n_files):
for idx, path in enumerate(data):
    if idx < 40:
        continue
    with path.open() as f:
        data = json.load(f)
    data["verified_page"] = False
    data["verified_url"] = False

    page_name = path.stem

    options = methods_of_fixing(page_name)
    page = None
    for possible_name in options:
        try:
            # It is very tempting to let auto_suggest=True because we
            #  get a lot more positives, but it introduces too much uncertainty.
            page = wikipedia.page(possible_name, auto_suggest=False)
        except wikipedia.exceptions.PageError:
            continue
        except wikipedia.exceptions.DisambiguationError:
            continue

        break

    if page is None:
        logging.warning(f"{idx}: Skipping '{page_name}', tried {options}")
        continue
    logging.info(f"{idx}: Mapping '{path.stem}' to '{page.title}' with '{possible_name}'")
    data["verified_page"] = page.title
    data["verified_url"] = page.url
