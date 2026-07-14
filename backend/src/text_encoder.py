"""
ONNX text encoder for the deployed FlagSearcher.

Uses the lightweight `tokenizers` runtime library (already a production dependency)
plus onnxruntime — no torch/transformers, so it fits the Render Starter footprint.
The ONNX graph bakes in CLS pooling + L2 normalization, so the output is directly
comparable by cosine (a plain dot product, since vectors are unit length).
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

# BGE v1.5 retrieval models expect this instruction on the query side only.
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class OnnxTextEncoder:
    def __init__(
        self,
        onnx_path: Path,
        tokenizer_path: Path,
        *,
        query_instruction: str = BGE_QUERY_INSTRUCTION,
        max_length: int = 128,
    ) -> None:
        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self._tokenizer.enable_truncation(max_length=max_length)
        self._tokenizer.enable_padding()
        self._query_instruction = query_instruction

        so = ort.SessionOptions()
        so.intra_op_num_threads = 1
        so.inter_op_num_threads = 1
        self._session = ort.InferenceSession(
            str(onnx_path), providers=["CPUExecutionProvider"], sess_options=so
        )

    def encode(self, texts: List[str], *, is_query: bool = False) -> np.ndarray:
        if is_query and self._query_instruction:
            texts = [self._query_instruction + t for t in texts]
        encodings = self._tokenizer.encode_batch(texts)
        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        out = self._session.run(None, {"input_ids": input_ids, "attention_mask": attention_mask})[0]
        return np.asarray(out, dtype=np.float32)
