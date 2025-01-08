#!/usr/bin/python
"""
Process all the files that we downloaded.
"""

import json
import logging
from pathlib import Path

# import coloredlogs
import wikipedia
from tqdm import tqdm
from utils import methods_of_fixing

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
    else:
        logging.info(f"{idx}: Mapping '{path.stem}' to '{page.title}' with '{possible_name}'")
        single_row["verified_page"] = page.title
        single_row["verified_url"] = page.url

    post_process_name.parent.mkdir(exist_ok=True, parents=True)
    with post_process_name.open("w") as f:
        json.dump(single_row, f, indent=1)
