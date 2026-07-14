#!/usr/bin/env python3
"""
Precompute the corpus text-description embeddings the deployed FlagSearcher ranks
against. Builds one document per flag (visual description; falls back to name when a
flag has no description yet), encodes with the deployed ONNX text encoder, and saves
a float32 matrix aligned to flags.json order.

Usage:
    uv run backend/scripts/generate_text_embeddings.py \
        --onnx backend/models/bge-small-en-v1.5.onnx \
        --tokenizer backend/models/bge-small-en-v1.5-tokenizer/tokenizer.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from backend.common.descriptions import build_document
from backend.common.flag_data import flaglist_from_json
from backend.src.text_encoder import OnnxTextEncoder

FLAGS_FILE = Path("backend/data/all_flags/flags.json")
OUT_FILE = Path("backend/data/all_flags/text_embeddings.npy")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--out", default=str(OUT_FILE))
    args = ap.parse_args()

    flags = flaglist_from_json(FLAGS_FILE).flags
    documents = [build_document(f.name, f.visual, include_name=False) for f in flags]

    encoder = OnnxTextEncoder(Path(args.onnx), Path(args.tokenizer))
    embeddings = encoder.encode(documents).astype(np.float32)
    # Normalize once at build time so the searcher only needs a dot product.
    embeddings /= np.clip(np.linalg.norm(embeddings, axis=1, keepdims=True), 1e-12, None)

    np.save(args.out, embeddings)
    described = sum(1 for f in flags if f.visual is not None)
    print(f"Saved {embeddings.shape} -> {args.out} ({described}/{len(flags)} flags described)")


if __name__ == "__main__":
    main()
