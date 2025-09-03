"""
Class that can take in an image and output a bunch of
other images of flags that look like it.
"""

from pathlib import Path

import numpy as np
import onnxruntime as ort

from backend.common.flag_data import FlagList, flaglist_from_json
from backend.src.minimal_tokenizer import create_minimal_tokenizer

FLAGS_FILE = Path("backend/data/national_flags/flags.json")
# FLAGS_FILE = Path("backend/data/commons_plus_national/flags.json")
MODEL_PATH = Path("backend/models/clip-text-encoder.onnx")


def cosine_similarity(a, b):
    """Simple cosine similarity implementation using numpy"""
    # Normalize vectors
    a_norm = a / np.linalg.norm(a, axis=-1, keepdims=True)
    b_norm = b / np.linalg.norm(b, axis=-1, keepdims=True)

    # Compute cosine similarity
    return np.dot(a_norm, b_norm.T)


class FlagSearcher:
    def __init__(self, top_k):
        self._top_k = top_k

        # Load ONNX model and tokenizer
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"ONNX model not found at {MODEL_PATH}. Please run the model conversion script."
            )

        self._session = ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])
        self._tokenizer = create_minimal_tokenizer()

        self._flags = flaglist_from_json(FLAGS_FILE)
        self._encoded_images = np.load(self._flags.embeddings_filename)

    def _encode_text(self, text):
        """Encode text using CLIP text encoder via ONNX"""
        inputs = self._tokenizer(text, return_tensors="np", padding=True, truncation=True)

        # Run inference
        outputs = self._session.run(
            None, {"input_ids": inputs["input_ids"], "attention_mask": inputs["attention_mask"]}
        )

        # The ONNX model now outputs the final embeddings directly
        # (including EOS token selection and text projection)
        text_embeddings = outputs[0]

        # Normalize embeddings
        text_embeddings = text_embeddings / np.linalg.norm(text_embeddings, axis=-1, keepdims=True)

        return text_embeddings

    def query(self, text_query, is_image) -> FlagList:
        """
        Run the recognizer, comparing to all the existing stuff.

        Arguments:
            text_query:
            is_image (bool): TODO(bjafek) this currently handles both text
                and image querying.

        Returns:
            FlagList
        """
        if is_image:
            raise NotImplementedError
            # TODO(bjafek) again, this should be a usable format when it
            #  gets passed, instead of this junk.
            # fn = "/home/bjafek/personal/draw_flags/examples/" + img.data
            # img = Image.open(fn)

        # Encode the text query using ONNX
        new_embedding = self._encode_text(text_query)

        # Calculate similarity with pre-computed embeddings
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
