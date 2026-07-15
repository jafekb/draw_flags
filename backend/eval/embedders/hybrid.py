"""
Hybrid retrieval: dense description similarity + a lexical name-match boost.

The pure text-description embedder is excellent on descriptive (medium/hard)
queries but weak on bare name queries ("flag of Japan") — a name is weak signal
against a visually-rich document. Adding a name-overlap term recovers name queries
without hurting descriptive ones, giving best-of-both.

final_score = cosine(query, description) + weight * name_overlap(query, flag_name)

name_overlap = fraction of a flag's meaningful name tokens present in the query
(generic tokens like "flag", "of", "the" ignored), so "the flag of japan" scores
1.0 against the flag named "Japan".
"""

from __future__ import annotations

from typing import List

import numpy as np

from backend.common.descriptions import build_document
from backend.common.flag_data import flaglist_from_json
from backend.common.name_match import build_name_token_sets, name_overlap_scores
from backend.eval.embedders.text_description import _get_model, _query_prefix
from backend.eval.run_eval import FLAGS_FILE, load_flag_names


class HybridExperiment:
    def __init__(self, model_name: str, weight: float, *, include_name_in_doc: bool) -> None:
        self.name = f"hybrid_{model_name.split('/')[-1]}_w{weight:g}"
        self._weight = weight
        self._flag_names = load_flag_names()
        self._model = _get_model(model_name)
        self._prefix = _query_prefix(model_name)

        flags = flaglist_from_json(FLAGS_FILE).flags
        documents = [build_document(f, include_name=include_name_in_doc) for f in flags]
        corpus = np.asarray(self._model.encode(documents, batch_size=64, show_progress_bar=False))
        self._corpus = corpus / np.clip(np.linalg.norm(corpus, axis=1, keepdims=True), 1e-12, None)
        self._name_token_sets = build_name_token_sets(self._flag_names)

    def rank(self, queries: List[str], top_k: int) -> List[List[str]]:
        prefixed = [self._prefix + q for q in queries] if self._prefix else queries
        q = np.asarray(self._model.encode(prefixed, batch_size=64, show_progress_bar=False))
        q = q / np.clip(np.linalg.norm(q, axis=1, keepdims=True), 1e-12, None)
        dense = q @ self._corpus.T  # (num_queries, num_flags)

        ranked = []
        for row, raw_query in zip(dense, queries):
            overlap = name_overlap_scores(raw_query, self._name_token_sets)
            score = row + self._weight * overlap
            top_idx = np.argsort(-score)[:top_k]
            ranked.append([self._flag_names[i] for i in top_idx])
        return ranked
