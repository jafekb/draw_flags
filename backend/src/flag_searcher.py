"""
Class that can take in an image and output a bunch of
other images of flags that look like it.
"""

import time
from pathlib import Path

from PIL import Image
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from backend.src.load_flags import load_all_flag_info
from common.flag_data import FlagList

ROOT_DIR = Path("/home/bjafek/personal/draw_flags/data/national_flags/data")


class FlagSearcher:
    def __init__(self, top_k, verbose=True):
        self._top_k = top_k

        # Load the OpenAI CLIP Model
        print("Loading CLIP Model...", end=" ")
        start = time.time()
        # TODO(bjafek) other models?
        self._model = SentenceTransformer("clip-ViT-B-32")
        if verbose:
            print(f"success ({time.time() - start:.2f}s)!")
            print("Loading & encoding images...", end=" ")
        start = time.time()
        self._image_list, self._flags = load_all_flag_info(root_dir=ROOT_DIR)
        if verbose:
            print(f"Images loaded ({time.time() - start:.2f}s)!")

        start = time.time()
        # TODO(bjafek) just store the embeddings
        self._encoded_images = self._model.encode(
            self._image_list,
            batch_size=128,
            convert_to_tensor=True,
            show_progress_bar=verbose,
        )

        if verbose:
            print(f"Images encoded ({time.time() - start:.2f}s)!")

    def query(self, img, is_image) -> FlagList:
        """
        Run the recognizer, comparing to all the existing stuff.

        Arguments:
            img:
            is_image (bool): TODO(bjafek) this currently handles both text
                and image querying.

        Returns:
            FlagList
        """
        if is_image:
            # TODO(bjafek) again, this should be a usable format when it
            #  gets passed, instead of this junk.
            fn = "/home/bjafek/personal/draw_flags/examples/" + img.data
            img = Image.open(fn)
        new_embedding = self._model.encode([img])
        similarity_scores = cosine_similarity(new_embedding, self._encoded_images)
        top_k_indices = similarity_scores.argsort()[0][::-1][: self._top_k]
        sorted_scores = similarity_scores.ravel()[top_k_indices].tolist()

        flags = []
        for ind, score in zip(top_k_indices, sorted_scores):
            # Use the stored Flag, just update the score with the similarity score.
            flag = self._flags.flags[ind]
            flag.score = score
            flags.append(flag)

        return FlagList(flags=flags)
