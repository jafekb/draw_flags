"""
Class that can take in an image and output a bunch of
other images of flags that look like it.
"""

import os
from pathlib import Path

import numpy as np
import onnxruntime as ort

from backend.common.flag_data import FlagList, flaglist_from_json
from backend.src.metadata_store import LocalMetadataStore
from backend.src.minimal_tokenizer import create_minimal_tokenizer
from backend.src.vector_index import HnswIndex

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
    def __init__(self, top_k, filtered_candidate_k=1000):
        self._top_k = top_k
        self._filtered_candidate_k = filtered_candidate_k

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
        self._metadata_store = LocalMetadataStore(self._flags)

        embeddings_path = Path(self._flags.embeddings_filename)
        index_path = embeddings_path.with_suffix(".hnsw.bin")
        self._vector_index = HnswIndex.load_or_build(self._encoded_images, index_path)

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

    def _matches_filters(self, flag, filters) -> bool:
        if not filters or all(v is None or v == [] for v in filters.values()):
            return True

        if filters.get("categories") and flag.category not in filters["categories"]:
            return False

        if filters.get("continent") and flag.continent != filters["continent"]:
            return False

        if filters.get("country"):
            is_national = flag.category == "national" and flag.name == filters["country"]
            is_from_country = flag.country == filters["country"]
            if not (is_national or is_from_country):
                return False

        return True

    def search_by_vector(self, vector, top_k, filters=None) -> FlagList:
        total_flags = len(self._flags.flags)
        if total_flags == 0:
            return FlagList(flags=[])
        top_k = min(top_k, total_flags)
        if filters and any(v is not None and v != [] for v in filters.values()):
            candidate_k = min(self._filtered_candidate_k, total_flags)
            ids, scores = self._vector_index.search(vector, candidate_k)
            flags = self._metadata_store.get_many(ids)

            filtered_flags = []
            for flag, score in zip(flags, scores):
                if not self._matches_filters(flag, filters):
                    continue
                filtered_flags.append(flag.model_copy(update={"score": score}))
                if len(filtered_flags) >= top_k:
                    break

            return FlagList(flags=filtered_flags)

        if top_k <= 0:
            return FlagList(flags=[])
        ids, scores = self._vector_index.search(vector, top_k)
        flags = self._metadata_store.get_many(ids)
        flags_with_score = [
            flag.model_copy(update={"score": score}) for flag, score in zip(flags, scores)
        ]
        return FlagList(flags=flags_with_score)

    def search_by_text(self, text_query, top_k, filters=None) -> FlagList:
        new_embedding = self._encode_text(text_query)
        return self.search_by_vector(new_embedding, top_k, filters=filters)

    def query(self, text_query, is_image, filters=None, top_k=None) -> FlagList:
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

        effective_top_k = self._top_k if top_k is None else top_k
        if effective_top_k <= 0:
            return FlagList(flags=[])
        return self.search_by_text(text_query, effective_top_k, filters=filters)
