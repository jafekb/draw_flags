#!/usr/bin/python
import re
import time
from pathlib import Path
from urllib.parse import unquote

import wikipedia
from Levenshtein import distance as levenshtein_distance
from tqdm import tqdm

from common.flag_data import Flag


def clean_img_url(url):
    """
    This is what it takes to get the page name from
    a normal image URL.
    """
    base_name = url.split("/")[-1].split(".")[0].replace("_", " ").split(".")[0]
    remove_parens = re.sub(r"%28.*?%29", "", base_name).strip()
    return unquote(remove_parens)


page = wikipedia.page("List of national flags of sovereign states")
images_on_page = page.images
images_on_page = [(i, clean_img_url(i)) for i in images_on_page]
ims = [i for i in page.images if "Flag_of" in i]
n_ims = len(ims)

out_dir = Path("/home/bjafek/personal/draw_flags/data/national_flags")
(out_dir / "images").mkdir(exist_ok=True)
(out_dir / "data").mkdir(exist_ok=True)

for idx, im in tqdm(enumerate(ims), total=n_ims):
    base = unquote(im.split("/")[-1]).replace(".svg", "").split("(")[0].replace("_", " ").strip()
    # Just 2 fixes are necessary
    if base == "Flag of Georgia":
        base = "Flag of Georgia (country)"
    elif base == "Flag of the Republic of Abkhazia":
        base = "Flag_of_Abkhazia"
    elif "Ivoire" in base:
        # TODO(bjafek) fix ivory coast / c'ote d'voire
        base = "Flag of Ivory Coast"

    flag_page = wikipedia.page(base, auto_suggest=False)

    image_url = min(images_on_page, key=lambda x: levenshtein_distance(flag_page.title, x[1]))[0]

    name = flag_page.title.replace("Flag of ", "")
    flag = Flag(
        name=name,
        wikipedia_page=base,
        wikipedia_url=flag_page.url,
        wikipedia_image_url=image_url,
        verification_method="table",
        score=1.0,
    )
    # And save the important stuff
    to_download = flag.save_image(out_dir / "images")
    flag.to_json(out_dir / "data")

    if to_download:
        time.sleep(1)  # sorry mr wikipedia sir won't bother you too much.
