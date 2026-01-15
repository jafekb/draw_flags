from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple

import hnswlib
import numpy as np


def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return vectors / norms


def _write_index_meta(meta_path: Path, *, dim: int, count: int, space: str) -> None:
    payload = {"dim": dim, "count": count, "space": space}
    meta_path.write_text(json.dumps(payload))


def _load_index_meta(meta_path: Path) -> dict:
    return json.loads(meta_path.read_text())


class VectorIndex:
    def search(self, vector: np.ndarray, top_k: int) -> Tuple[List[int], List[float]]:
        raise NotImplementedError


class HnswIndex(VectorIndex):
    def __init__(self, index: hnswlib.Index, dim: int) -> None:
        self._index = index
        self._dim = dim

    @classmethod
    def load_or_build(
        cls,
        embeddings: Optional[np.ndarray],
        index_path: Path,
        meta_path: Path,
        *,
        ef_search: int = 200,
        ef_construction: int = 200,
        m: int = 16,
    ) -> "HnswIndex":
        space = "cosine"
        if index_path.exists():
            if meta_path.exists():
                meta = _load_index_meta(meta_path)
                dim = int(meta["dim"])
                index = hnswlib.Index(space=space, dim=dim)
                index.load_index(str(index_path))
                index.set_ef(ef_search)
                return cls(index=index, dim=dim)

            if embeddings is None:
                raise FileNotFoundError(
                    f"Index metadata not found at {meta_path}; embeddings required to rebuild."
                )

        if embeddings is None:
            raise FileNotFoundError(
                f"Embeddings required to build index at {index_path} (missing)."
            )

        embeddings = np.asarray(embeddings, dtype=np.float32)
        embeddings = normalize_vectors(embeddings)
        dim = embeddings.shape[1]

        index = hnswlib.Index(space=space, dim=dim)
        if index_path.exists():
            index.load_index(str(index_path))
            if index.get_current_count() != embeddings.shape[0]:
                index = hnswlib.Index(space=space, dim=dim)
                index.init_index(
                    max_elements=embeddings.shape[0],
                    ef_construction=ef_construction,
                    M=m,
                )
                index.add_items(embeddings, np.arange(embeddings.shape[0]))
                index.save_index(str(index_path))
        else:
            index.init_index(
                max_elements=embeddings.shape[0],
                ef_construction=ef_construction,
                M=m,
            )
            index.add_items(embeddings, np.arange(embeddings.shape[0]))
            index.save_index(str(index_path))

        _write_index_meta(meta_path, dim=dim, count=embeddings.shape[0], space=space)
        index.set_ef(ef_search)
        return cls(index=index, dim=dim)

    def search(self, vector: np.ndarray, top_k: int) -> Tuple[List[int], List[float]]:
        query = np.asarray(vector, dtype=np.float32)
        if query.ndim == 1:
            query = query.reshape(1, -1)
        if query.shape[1] != self._dim:
            raise ValueError(f"Query dim {query.shape[1]} does not match index dim {self._dim}")
        query = normalize_vectors(query)

        labels, distances = self._index.knn_query(query, k=top_k)
        ids = labels[0].tolist()
        scores = (1.0 - distances[0]).tolist()
        return ids, scores
