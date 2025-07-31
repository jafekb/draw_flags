"""
Class that can take in an image and output a bunch of
other images of flags that look like it.
"""

from pathlib import Path

import numpy as np
import onnxruntime as ort
from sentence_transformers import SentenceTransformer
from common.flag_data import FlagList, flaglist_from_json
from sklearn.metrics.pairwise import cosine_similarity
from transformers import CLIPTokenizer

FLAGS_FILE = Path("data/national_flags/flags.json")
# FLAGS_FILE = Path("backend/data/commons_plus_national/flags.json")


class FlagSearcher:
    def __init__(self, top_k):
        self._top_k = top_k

        # Load ONNX model and tokenizer
        model_path = "models/clip-text-encoder.onnx"
        if not Path(model_path).exists():
            raise FileNotFoundError(f"ONNX model not found at {model_path}. Please run the model conversion script.")

        self._session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self._tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32")

        self._flags = flaglist_from_json(FLAGS_FILE)
        self._encoded_images = np.load(self._flags.embeddings_filename)
        self._model = SentenceTransformer("clip-ViT-B-32")

    def _encode_text(self, text):
        """Encode text using CLIP text encoder via ONNX"""
        inputs = self._tokenizer(text, return_tensors="np", padding=True, truncation=True)

        # Run inference
        outputs = self._session.run(None, {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"]
        })

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

        # Encode the text query
        new_embedding = self._encode_text(text_query)
        orig_embedding = self._model.encode([text_query])
        
        # Debug: Check similarity between ONNX and sentence-transformers
        similarity = cosine_similarity(new_embedding, orig_embedding)[0][0]
        print(f"ONNX vs Sentence-transformers similarity: {similarity:.6f}")

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
