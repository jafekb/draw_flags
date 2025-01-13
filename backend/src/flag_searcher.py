"""
Class that can take in an image and output a bunch of
other images of flags that look like it.
"""

from pathlib import Path

import torch
from PIL import Image
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from common.flag_data import FlagList, flaglist_from_json

FLAGS_FILE = Path("/home/bjafek/personal/draw_flags/data/national_flags/flag_searcher/flags.json")


class FlagSearcher:
    def __init__(self, top_k, verbose=True):
        self._top_k = top_k
        self._verbose = verbose

        # TODO(bjafek) pull out name to a config
        self._model = SentenceTransformer("clip-ViT-B-32")

        self._flags = flaglist_from_json(FLAGS_FILE)
        self._encoded_images = torch.load(self._flags.embeddings_filename, weights_only=True)

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
