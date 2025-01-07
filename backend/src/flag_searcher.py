"""
Class that can take in an image and output a bunch of
other images of flags that look like it.

Uses:
https://docs.openflags.net/implementations/python/
"""

from pathlib import Path
from PIL import Image
import time

import cairosvg
import open_flags as of
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

from src.utils import Flag, Flags

TMP_DIR = Path("/home/bjafek/personal/draw_flags/tmp")
TMP_DIR.mkdir(exist_ok=True, parents=False)


def load_all_flag_info():
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


class FlagSearcher:
    def __init__(self, top_k):
        self._top_k = top_k

        # Load the OpenAI CLIP Model
        print("Loading CLIP Model...", end=" ")
        start = time.time()
        # TODO(bjafek) other models?
        self._model = SentenceTransformer("clip-ViT-B-32")
        print(f"success ({time.time() - start:.2f}s)!")

        print("Loading & encoding images...", end=" ")
        start = time.time()
        self._image_list, self._label_list = load_all_flag_info()
        print(f"Images loaded ({time.time() - start:.2f}s)!")

        start = time.time()
        # TODO(bjafek) just store the embeddings
        self._encoded_images = self._model.encode(
            self._image_list,
            batch_size=128,
            convert_to_tensor=True,
            show_progress_bar=True,
        )
        print(f"Images encoded ({time.time() - start:.2f}s)!")

    def query(self, img, is_image) -> Flags:
        """
        Run the recognizer, comparing to all the existing stuff.

        Arguments:
            img:
            is_image (bool): TODO(bjafek) this currently handles both text
                and image querying.

        Returns:
            Flags
        """
        if is_image:
            # TODO(bjafek) again, this should be a usable format when it
            #  gets passed, instead of this junk.
            fn = "/home/bjafek/personal/draw_flags/examples/" + img.data
            img = Image.open(fn)
        new_embedding = self._model.encode([img])
        similarity_scores = cosine_similarity(new_embedding, self._encoded_images)
        top_k_indices = similarity_scores.argsort()[0][::-1][: self._top_k]
        sorted_scores = similarity_scores.ravel()[top_k_indices]

        flags = []
        for ind, score in zip(top_k_indices, sorted_scores):
            flag = Flag(
                name=self._label_list[ind],
                score=score,
            )
            flags.append(flag)

        return Flags(flags=flags)
