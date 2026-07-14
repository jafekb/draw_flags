"""
Deploy-faithful hybrid experiment: same code path as the production FlagSearcher
(ONNX encoder via the `tokenizers` lib + name-match rerank), so eval numbers reflect
exactly what ships. Used to confirm int8 quantization doesn't hurt quality.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np

from backend.common.descriptions import build_document, load_descriptions
from backend.common.flag_data import flaglist_from_json
from backend.common.name_match import (
    build_name_token_sets,
    name_overlap_scores,
    national_prior,
)
from backend.eval.run_eval import FLAGS_FILE, load_flag_names
from backend.src.text_encoder import OnnxTextEncoder


class OnnxHybridExperiment:
    def __init__(
        self,
        name: str,
        onnx_path: str,
        tokenizer_path: str,
        weight: float,
        national_bonus: float = 0.0,
    ) -> None:
        self.name = name
        self._weight = weight
        flags = flaglist_from_json(FLAGS_FILE).flags
        self._flag_names = load_flag_names()
        self._encoder = OnnxTextEncoder(Path(onnx_path), Path(tokenizer_path))

        descriptions = load_descriptions()
        documents = [
            build_document(n, descriptions.get(n), include_name=False) for n in self._flag_names
        ]
        corpus = self._encoder.encode(documents)
        self._corpus = corpus / np.clip(np.linalg.norm(corpus, axis=1, keepdims=True), 1e-12, None)
        self._name_token_sets = build_name_token_sets(self._flag_names)
        self._prior = national_prior([f.category for f in flags], national_bonus)

    def rank(self, queries: List[str], top_k: int) -> List[List[str]]:
        q = self._encoder.encode(queries, is_query=True)
        q = q / np.clip(np.linalg.norm(q, axis=1, keepdims=True), 1e-12, None)
        dense = q @ self._corpus.T
        ranked = []
        for row, raw_query in zip(dense, queries):
            score = (
                row
                + self._weight * name_overlap_scores(raw_query, self._name_token_sets)
                + self._prior
            )
            top_idx = np.argsort(-score)[:top_k]
            ranked.append([self._flag_names[i] for i in top_idx])
        return ranked
