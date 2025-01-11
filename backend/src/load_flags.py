"""
For loading the flags that I have found.

Uses:
https://docs.openflags.net/implementations/python/
"""

import json
from pathlib import Path
from shutil import copyfile

import cairosvg
import open_flags as of
from PIL import Image
from tqdm import tqdm

OPEN_FLAGS_TMP_DIR = Path("/home/bjafek/personal/draw_flags/tmp")
OPEN_FLAGS_TMP_DIR.mkdir(exist_ok=True, parents=False)

WIKIMEDIA_COMMONS_DIR = Path(
    "/home/bjafek/personal/draw_flags/data_mining/wikimedia-downloader/commons_verified/data"
)
WIKIMEDIA_COMMONS_IMAGES = Path(
    "/home/bjafek/personal/draw_flags/data_mining/wikimedia-downloader/commons_verified/images"
)


def load_all_flag_info(mode):
    """
    Loads the flag info according to the method the user specifies.
    """
    if mode == "open_flags":
        return load_open_flags()
    if mode == "wikimedia_commons":
        return load_wikimedia_commons()
    raise ValueError(f"Unrecognized mode '{mode}'!")


def get_image(img_path: Path):
    out_base = img_path.stem.lower().replace(" ", "_").replace(",", "")
    final_path = WIKIMEDIA_COMMONS_IMAGES / f"{out_base}.png"

    if img_path.suffix in (".svg", ".SVG"):
        # The other types just work.
        with img_path.open() as f:
            svg = f.read()
        try:
            cairosvg.svg2png(svg, write_to=str(final_path))
        except Exception:
            print(out_base, "failed!")
            return None

    if not final_path.is_file():
        copyfile(img_path, final_path)

    assert final_path.is_file()
    return final_path


def load_wikimedia_commons(verification_methods=("commons",)):
    """
    Load flags through wikimedia commons
    # TODO(bjafek) we should use the Flag and Flags dataclasses

    Returns:
        image_list
        label_list
    """
    all_jsons = list(WIKIMEDIA_COMMONS_DIR.rglob("*.json"))
    n_files = len(all_jsons)
    image_list = []
    label_list = []

    for idx, fn in tqdm(enumerate(all_jsons), total=n_files):
        with fn.open() as f:
            data = json.load(f)
        if data.get("verification_method", None) not in verification_methods:
            continue

        label_list.append(data["verified_page"])

        # TODO(bjafek) this should happen during a separate processing step,
        #  NOT during loading.
        img_path = get_image(Path(data["image_path"]))
        if img_path is None:
            continue

        img = Image.open(img_path)
        image_list.append(img)
    return image_list, label_list


def load_open_flags():
    """
    Load flags through open_flags
    # TODO(bjafek) we should use the Flag and Flags dataclasses

    Returns:
        image_list
        label_list
    """
    image_list = []
    label_list = []
    idx = 0
    for key, val in tqdm(of.flag_map.FLAG_MAP.items()):
        country, place = key.split("/")
        file_path = OPEN_FLAGS_TMP_DIR / country / f"{place}.svg"
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
