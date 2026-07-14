"""
Flag search: given a text query, return flags whose visual description best matches.

Hybrid ranking = dense cosine similarity between the query embedding and each flag's
VLM description embedding, plus a lexical name-match boost so name queries ("flag of
Japan") work too. Runs on the small ONNX text encoder + a precomputed, normalized
description-embedding matrix, so it fits the Render Starter 512 MB / 0.5 CPU budget.
"""

import os
from pathlib import Path

import numpy as np

from backend.common.flag_data import FlagList, flaglist_from_json
from backend.common.name_match import build_name_token_sets, name_overlap_scores
from backend.src.metadata_store import LocalMetadataStore, compute_flag_id
from backend.src.text_encoder import OnnxTextEncoder

FLAGS_FILE = Path("backend/data/all_flags/flags.json")
TEXT_EMBEDDINGS_FILE = Path("backend/data/all_flags/text_embeddings.npy")
MODEL_PATH = Path("backend/models/bge-base-en-v1.5-int8.onnx")
TOKENIZER_PATH = Path("backend/models/bge-base-en-v1.5-tokenizer/tokenizer.json")
DEFAULT_NAME_MATCH_WEIGHT = 0.3


class FlagSearcher:
    def __init__(self, top_k, name_match_weight: float = DEFAULT_NAME_MATCH_WEIGHT):
        self._top_k = top_k
        self._weight = float(os.getenv("NAME_MATCH_WEIGHT", str(name_match_weight)))

        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Text encoder not found at {MODEL_PATH}.")
        if not TEXT_EMBEDDINGS_FILE.exists():
            raise FileNotFoundError(
                f"Description embeddings not found at {TEXT_EMBEDDINGS_FILE}. "
                "Run backend/scripts/generate_text_embeddings.py."
            )

        self._encoder = OnnxTextEncoder(MODEL_PATH, TOKENIZER_PATH)
        self._flags = flaglist_from_json(FLAGS_FILE)
        self._metadata_store = LocalMetadataStore(self._flags)
        self._stable_ids = [compute_flag_id(f) for f in self._flags.flags]

        # Corpus embeddings are saved already L2-normalized, so dense cosine is a dot.
        self._corpus = np.load(TEXT_EMBEDDINGS_FILE).astype(np.float32)
        self._name_token_sets = build_name_token_sets([f.name for f in self._flags.flags])

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

    def _scores(self, text_query: str) -> np.ndarray:
        q = self._encoder.encode([text_query], is_query=True)[0]
        q = q / max(float(np.linalg.norm(q)), 1e-12)
        dense = self._corpus @ q
        overlap = name_overlap_scores(text_query, self._name_token_sets)
        return dense + self._weight * overlap

    def search_by_text(self, text_query, top_k, filters=None) -> FlagList:
        scores = self._scores(text_query)
        order = np.argsort(-scores)
        results = []
        for idx in order:
            flag = self._flags.flags[idx]
            if not self._matches_filters(flag, filters):
                continue
            results.append(
                flag.model_copy(update={"score": float(scores[idx]), "id": self._stable_ids[idx]})
            )
            if len(results) >= top_k:
                break
        return FlagList(flags=results)

    def query(self, text_query, is_image, filters=None, top_k=None) -> FlagList:
        """
        Search for flags matching the query, with optional filtering.

        Arguments:
            text_query: Text description of the flag.
            is_image (bool): image querying is not yet supported.
            filters: Optional dict with keys: categories, continent, country.

        Returns:
            FlagList with up to top_k matching flags, best first.
        """
        if is_image:
            raise NotImplementedError

        effective_top_k = self._top_k if top_k is None else top_k
        if effective_top_k <= 0:
            return FlagList(flags=[])
        return self.search_by_text(text_query, effective_top_k, filters=filters)

    def all_flags(self) -> FlagList:
        return self._flags
