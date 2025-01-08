#!/usr/bin/python
"""
I ABANDONED THIS IN FAVOR OF THE WIKIMEDIA-DOWNLOADER.

Scrape wikipedia using the `wikipedia` pip package

Pages I'm interested in:
1. https://en.wikipedia.org/wiki/List_of_flags_by_design
2. https://en.wikipedia.org/wiki/List_of_flag_names
3. https://en.wikipedia.org/wiki/Flag_families
4. https://en.wikipedia.org/wiki/List_of_national_flags_of_sovereign_states
5. https://en.wikipedia.org/wiki/Gallery_of_flags_of_dependent_territories
6. https://en.wikipedia.org/wiki/Lists_of_country_subdivision_flags
    a. https://en.wikipedia.org/wiki/List_of_country_subdivision_flags_in_Asia
    b. https://en.wikipedia.org/wiki/List_of_country_subdivision_flags_in_Europe
    c. https://en.wikipedia.org/wiki/List_of_country_subdivision_flags_in_North_America
    d. https://en.wikipedia.org/wiki/List_of_country_subdivision_flags_in_Oceania
    e. https://en.wikipedia.org/wiki/List_of_country_subdivision_flags_in_South_America
"""

import time
from pathlib import Path

import pandas as pd
import wikipedia
from tqdm import tqdm

start = time.time()
N = 10_000


def get_good_flags():
    good_flag_name = Path("./good_flags.csv")
    if good_flag_name.is_file():
        return pd.read_csv(good_flag_name, header=None)

    search_queries = [
        "Flag of",
        "Flag",
        "Flags",
        "Flag of Europe",
        "State flags USA",
        "Flag of Africa",
        "Flag of Oceania",
        "Flag of North America",
        "Flag of South America",
        "Miscellaneous flag",
        "Pride flag",
        "Confederate flag",
        "Flag design",
    ]

    all_results = []
    for query in tqdm(search_queries):
        res = wikipedia.search(query, results=N)
        time.sleep(2)
        all_results.extend(res)
    all_results = list(set(all_results))

    # this should have ~630 values
    good = [i for i in all_results if i.lower().startswith("flag of")]
    good.sort()

    with good_flag_name.open("w") as f:
        for line in good:
            f.write(f"{line}\n")
    return good


def save_info(flags):
    """ """
    for page in flags:
        pass


good_flags = get_good_flags()
