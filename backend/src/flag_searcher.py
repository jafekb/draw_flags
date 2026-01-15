"""
Class that can take in an image and output a bunch of
other images of flags that look like it.
"""

import os
from pathlib import Path

import numpy as np
import onnxruntime as ort

from backend.common.flag_data import FlagList, flaglist_from_json
from backend.src.minimal_tokenizer import create_minimal_tokenizer

FLAGS_FILE = Path("backend/data/comprehensive_flags_3/flags.json")
MODEL_PATH = Path("backend/models/clip-text-encoder.onnx")


def cosine_similarity(a, b):
    """Simple cosine similarity implementation using numpy"""
    # Normalize vectors, handling zero vectors
    a_norm_val = np.linalg.norm(a, axis=-1, keepdims=True)
    b_norm_val = np.linalg.norm(b, axis=-1, keepdims=True)

    # Replace zero norms with 1 to avoid division by zero (will result in 0 similarity)
    a_norm_val = np.where(a_norm_val == 0, 1, a_norm_val)
    b_norm_val = np.where(b_norm_val == 0, 1, b_norm_val)

    a_norm = a / a_norm_val
    b_norm = b / b_norm_val

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

        session_options = ort.SessionOptions()
        session_options.enable_cpu_mem_arena = False
        session_options.enable_mem_pattern = False
        session_options.intra_op_num_threads = int(os.getenv("ORT_INTRA_OP_NUM_THREADS", "1"))
        session_options.inter_op_num_threads = int(os.getenv("ORT_INTER_OP_NUM_THREADS", "1"))
        self._session = ort.InferenceSession(
            str(MODEL_PATH),
            providers=["CPUExecutionProvider"],
            sess_options=session_options,
        )
        self._tokenizer = create_minimal_tokenizer()

        self._flags = flaglist_from_json(FLAGS_FILE)
        self._encoded_images = np.load(self._flags.embeddings_filename, mmap_mode="r")

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

    def _get_filtered_indices(self, filters):
        """
        Return indices of flags matching the filters.
        Filters BEFORE computing similarities for efficiency.

        Args:
            filters: Dict with optional keys: categories, continent, country

        Returns:
            List[int]: Indices of matching flags
        """
        if not filters or all(v is None or v == [] for v in filters.values()):
            return list(range(len(self._flags.flags)))

        matching_indices = []

        for idx, flag in enumerate(self._flags.flags):
            # Category filter
            if filters.get("categories") and flag.category not in filters["categories"]:
                continue
            
            # Continent filter
            if filters.get("continent") and flag.continent != filters["continent"]:
                continue
            
            # Country filter (national flag OR from that country)
            if filters.get("country"):
                is_national = flag.category == "national" and flag.name == filters["country"]
                is_from_country = flag.country == filters["country"]
                if not (is_national or is_from_country):
                    continue

            matching_indices.append(idx)

        return matching_indices

    def query(self, text_query, is_image, filters=None) -> FlagList:
        """
        Search for flags matching the query, with optional filtering.

        Filters are applied BEFORE computing similarities for efficiency.

        Arguments:
            text_query: Text description of the flag
            is_image (bool): TODO(bjafek) this currently handles both text
                and image querying.
            filters: Optional dict with keys: categories, continent, country

        Returns:
            FlagList with top_k matching flags
        """
        if is_image:
            raise NotImplementedError
            # TODO(bjafek) again, this should be a usable format when it
            #  gets passed, instead of this junk.
            # fn = "/home/bjafek/personal/draw_flags/examples/" + img.data
            # img = Image.open(fn)

        # 1. Get indices of flags matching filters
        filtered_indices = self._get_filtered_indices(filters)

        # Handle empty filter results
        if len(filtered_indices) == 0:
            return FlagList(flags=[])

        # 2. Extract embeddings for filtered flags only
        filtered_embeddings = self._encoded_images[filtered_indices]

        # 3. Encode the text query
        new_embedding = self._encode_text(text_query)

        # 4. Compute similarities ONLY on filtered embeddings
        similarity_scores = cosine_similarity(new_embedding, filtered_embeddings)

        # 5. Get top K from filtered set
        num_results = min(self._top_k, len(filtered_indices))
        top_k_local_indices = similarity_scores.argsort()[0][::-1][:num_results]
        sorted_scores = similarity_scores.ravel()[top_k_local_indices].tolist()

        # 6. Map back to original flags and add scores
        flags = []
        for local_idx, score in zip(top_k_local_indices, sorted_scores):
            original_idx = filtered_indices[local_idx]
            flag = self._flags.flags[original_idx]
            flag_with_score = flag.model_copy(update={"score": score})
            flags.append(flag_with_score)

        return FlagList(flags=flags)
