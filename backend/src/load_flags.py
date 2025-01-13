"""
For loading the flags that I have found.

Uses:
https://docs.openflags.net/implementations/python/
"""

from pathlib import Path

from PIL import Image
from tqdm import tqdm

from common.flag_data import FlagList, flag_from_json

OPEN_FLAGS_TMP_DIR = Path("/home/bjafek/personal/draw_flags/tmp")
OPEN_FLAGS_TMP_DIR.mkdir(exist_ok=True, parents=False)

WIKIMEDIA_COMMONS_DIR = Path(
    "/home/bjafek/personal/draw_flags/data_mining/wikimedia-downloader/commons_verified/data"
)
WIKIMEDIA_COMMONS_IMAGES = Path(
    "/home/bjafek/personal/draw_flags/data_mining/wikimedia-downloader/commons_verified/images"
)


def load_all_flag_info(root_dir):
    """
    This is now the accepted way to do this.
    # TODO(bjafek) use the FlagList object instead of this
    # TODO(bjafek) If you want to load open_flags or wikimedia_commons,
        you need to align with this format.

    Returns:
        image_list
        label_list
    """
    jsons = list(root_dir.rglob("*.json"))
    n_jsons = len(jsons)
    image_list = []
    flags = []
    for idx, fn in tqdm(enumerate(jsons), total=n_jsons):
        flag = flag_from_json(fn)

        flags.append(flag)

        # TODO(bjafek) I don't totally understand the format that the model encode expects
        # lmao I think the reason it expects a string is because I'm using the
        # SentenceTransformer instead of an ImageTransformer. But in practice i
        # works pretty well.
        img = Image.open(flag.local_image_link)
        image_list.append(img)
    return image_list, FlagList(flags=flags)
