#!/usr/bin/python
import re
import time
from pathlib import Path
from urllib.parse import unquote

import wikipedia
from common.flag_data import Flag
from tqdm import tqdm


def clean_img_url(url):
    """
    This is what it takes to get the page name from
    a normal image URL.
    """
    base_name = url.split("/")[-1].split(".")[0].replace("_", " ").split(".")[0]
    remove_parens = re.sub(r"%28.*?%29", "", base_name).strip()
    return unquote(remove_parens)


page = wikipedia.page("List of country subdivision flags in North America")
images_on_page = page.images
images_on_page = [(i, clean_img_url(i)) for i in images_on_page]
ims = [i for i in page.images if "Flag_of" in i]
n_ims = len(ims)

out_dir = Path("/home/bjafek/personal/draw_flags/data/north_american_flags")
out_dir.mkdir(exist_ok=True)
(out_dir / "images").mkdir(exist_ok=True)
(out_dir / "data").mkdir(exist_ok=True)

for idx, img_url in tqdm(enumerate(ims), total=n_ims):
    base = (
        unquote(img_url.split("/")[-1])
        .replace(".svg", "")
        .replace(".png", "")
        .replace(".gif", "")
        .split("(")[0]
        .replace("_", " ")
        .strip()
    )

    try:
        flag_page = wikipedia.page(base, auto_suggest=True)
    except wikipedia.exceptions.PageError:
        try:
            flag_page = wikipedia.page(base.replace("Flag of ", ""), auto_suggest=True)
        except wikipedia.exceptions.PageError:
            # Just give up for now :(
            print(f"Skipping {base}, couldn't find it")
            continue

    name = flag_page.title.replace("Flag of ", "")
    # TODO(bjafek) does a weird thing with 'Flag of Bequia' that I had to manually fix
    # TODO(bjafek) there are actually quite a few errors here that I'd like to improve.
    flag = Flag(
        name=name,
        wikipedia_page=base,
        wikipedia_url=flag_page.url,
        wikipedia_image_url=img_url,
        verification_method="table",
        score=1.0,
    )
    # And save the important stuff
    to_download = flag.save_image(out_dir / "images")
    flag.to_json(out_dir / "data")

    if to_download:
        time.sleep(1)  # sorry mr wikipedia sir won't bother you too much.
