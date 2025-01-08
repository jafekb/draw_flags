#!/usr/bin/python
"""
Process all the files that we downloaded.
"""

import json
import logging
from pathlib import Path

# import coloredlogs
import pandas as pd
import wikipedia
from tqdm import tqdm
from utils import methods_of_fixing

# coloredlogs.install()

# TODO(bjafek) make a constants.py instead of re-defining here.
OUT_DIR = Path("/home/bjafek/personal/draw_flags/data_mining/wikimedia-downloader/output")

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


data = sorted(OUT_DIR.rglob("*.json"))
n_files = len(data)

all_rows = []

for idx, path in tqdm(enumerate(data), total=n_files):
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

    # Just save progress every once in awhile.
    if idx % 100 == 0:
        df = pd.DataFrame(all_rows)
        df.to_csv("more_info.csv", index=False)

    all_rows.append(single_row)

df = pd.DataFrame(all_rows)
df.to_csv("more_info.csv", index=False)
