"""
For loading the flags that I have found.

Uses:
https://docs.openflags.net/implementations/python/
"""

from pathlib import Path

import cairosvg
import open_flags as of
from PIL import Image
from tqdm import tqdm

TMP_DIR = Path("/home/bjafek/personal/draw_flags/tmp")
TMP_DIR.mkdir(exist_ok=True, parents=False)


def load_all_flag_info(mode):
    """
    Loads the flag info according to the method the user specifies.
    """
    if mode == "open_flags":
        return load_open_flags()
    if mode == "wikimedia_commons":
        return load_wikimedia_commons()
    raise ValueError(f"Unrecognized mode '{mode}'!")


def load_wikimedia_commons():
    """
    Load flags through wikimedia commons
    # TODO(bjafek) we should use the Flag and Flags dataclasses
    """
    raise NotImplementedError


def load_open_flags():
    """
    Load flags through open_flags
    # TODO(bjafek) we should use the Flag and Flags dataclasses
    """
    image_list = []
    label_list = []
    idx = 0
    for key, val in tqdm(of.flag_map.FLAG_MAP.items()):
        country, place = key.split("/")
        file_path = TMP_DIR / country / f"{place}.svg"
        file_path.parent.mkdir(exist_ok=True, parents=False)

        if not file_path.exists():
            svg = of.get_flag_svg(country, place)
            try:
                # https://cairosvg.org/documentation/
                img = cairosvg.svg2png(svg, write_to=str(file_path))
            except Exception:
                print(key, "failed!")
                continue

        # TODO(bjafek) I don't totally understand the format that the model encode expects
        # lmao I think the reason it expects a string is because I'm using the SentenceTransformer
        # instead of an ImageTransformer
        img = Image.open(file_path)
        image_list.append(img)
        label_list.append(key)
        idx += 1
    return image_list, label_list
