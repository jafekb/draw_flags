"""
Text-to-text retrieval experiment: embed each flag's VLM description with a
sentence-transformer, embed the query with the same model, rank by cosine.

This is the primary hypothesis for beating the CLIP baseline — it turns the hard
cross-modal (text->image) problem into an easy same-modal (text->text) one.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

import numpy as np

from backend.common.descriptions import build_document
from backend.common.flag_data import flaglist_from_json
from backend.eval.run_eval import FLAGS_FILE, EmbeddingExperiment, load_flag_names

# BGE v1.5 retrieval models expect a query-side instruction; passages get none.
# Omitting it noticeably degrades ranking (especially short name queries).
_BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


def _query_prefix(model_name: str) -> str:
    return _BGE_QUERY_INSTRUCTION if "bge" in model_name.lower() else ""


@lru_cache(maxsize=4)
def _get_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def make_text_description_experiment(
    model_name: str = "BAAI/bge-small-en-v1.5",
    *,
    include_name: bool = True,
    label: str | None = None,
) -> EmbeddingExperiment:
    flag_names = load_flag_names()
    flags = flaglist_from_json(FLAGS_FILE).flags
    model = _get_model(model_name)

    documents = [build_document(f, include_name=include_name) for f in flags]
    corpus = np.asarray(model.encode(documents, batch_size=64, show_progress_bar=False))

    prefix = _query_prefix(model_name)

    def encode_queries(queries: List[str]) -> np.ndarray:
        prefixed = [prefix + q for q in queries] if prefix else queries
        return np.asarray(model.encode(prefixed, batch_size=64, show_progress_bar=False))

    short_model = model_name.split("/")[-1]
    name = label or f"textdesc_{short_model}{'_name' if include_name else ''}"
    return EmbeddingExperiment(name, corpus, encode_queries, flag_names)
