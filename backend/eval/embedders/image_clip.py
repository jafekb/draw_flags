"""
Cross-modal image-embedding experiments: embed each flag *image* with a CLIP-style
model and the text query with the same model's text tower, rank by cosine.

Covers the baseline backbone (clip-ViT-B-32) and stronger ones (larger OpenCLIP,
SigLIP) so we can measure how far a better backbone alone gets us versus the
text-description approach. Image embeddings are cached to disk per model so the
expensive encode runs once.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np

from backend.eval.run_eval import EmbeddingExperiment, load_flag_names
from backend.scripts.download_images import IMAGES_DIR, safe_name

FLAGS_FILE = Path("backend/data/all_flags/flags.json")
CACHE_DIR = Path("backend/data/all_flags/experiment_embeddings")


def _find_image(name: str) -> Path | None:
    stem = safe_name(name)
    for ext in (".png", ".jpg", ".jpeg", ".gif"):
        candidate = IMAGES_DIR / f"{stem}{ext}"
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return None


def _load_images(flag_names: List[str]):
    from PIL import Image

    images, valid_idx = [], []
    for i, name in enumerate(flag_names):
        path = _find_image(name)
        if path is None:
            continue
        try:
            images.append(Image.open(path).convert("RGB"))
            valid_idx.append(i)
        except Exception:
            continue
    return images, valid_idx


def make_sentence_transformers_clip(model_name: str = "clip-ViT-B-32") -> EmbeddingExperiment:
    """OpenAI/OpenCLIP models exposed through sentence-transformers (image + text)."""
    from sentence_transformers import SentenceTransformer

    flag_names = load_flag_names()
    model = SentenceTransformer(model_name)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"img_{model_name.replace('/', '_')}.npy"
    if cache.exists():
        corpus = np.load(cache)
    else:
        images, valid_idx = _load_images(flag_names)
        emb = np.asarray(model.encode(images, batch_size=32, show_progress_bar=True))
        # Place encoded rows back into full-corpus positions; missing images -> zeros
        # (a zero vector never wins a cosine ranking).
        corpus = np.zeros((len(flag_names), emb.shape[1]), dtype=np.float32)
        corpus[np.array(valid_idx)] = emb
        np.save(cache, corpus)

    def encode_queries(queries: List[str]) -> np.ndarray:
        return np.asarray(model.encode(queries, batch_size=64, show_progress_bar=False))

    label = f"image_{model_name.split('/')[-1]}"
    return EmbeddingExperiment(label, corpus, encode_queries, flag_names)
