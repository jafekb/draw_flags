#!/usr/bin/env python3
"""
Export a sentence-transformers text embedding model (default BGE) to ONNX for the
deployed FlagSearcher. BGE v1.5 uses CLS pooling + L2 normalization; we bake both
into the graph so onnxruntime output matches sentence-transformers exactly.

Verifies parity against sentence-transformers before saving, and reports the ONNX
file size (deploy footprint matters — Render Starter is 512 MB RAM).

Usage:
    uv run backend/scripts/convert_text_encoder_onnx.py --model BAAI/bge-small-en-v1.5
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

MODELS_DIR = Path("backend/models")


class ClsPooledEncoder(torch.nn.Module):
    """Transformer -> CLS token -> L2 normalize (matches BGE sentence-transformers)."""

    def __init__(self, model: torch.nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(self, input_ids, attention_mask):
        out = self.model(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0]
        return torch.nn.functional.normalize(cls, p=2, dim=1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    ap.add_argument("--out", default=None, help="Output .onnx path (fp32)")
    ap.add_argument("--int8", action="store_true", help="Also emit an int8-quantized model")
    args = ap.parse_args()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    short = args.model.split("/")[-1]
    onnx_path = Path(args.out) if args.out else MODELS_DIR / f"{short}.onnx"

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    # Save tokenizer next to the model so the deployed encoder (tokenizers lib) can load it.
    tokenizer.save_pretrained(str(MODELS_DIR / f"{short}-tokenizer"))
    model = AutoModel.from_pretrained(args.model)
    encoder = ClsPooledEncoder(model).eval()

    sample = ["green flag with a white crescent and star", "the flag of japan"]
    enc = tokenizer(sample, return_tensors="pt", padding=True, truncation=True, max_length=128)

    torch.onnx.export(
        encoder,
        (enc["input_ids"], enc["attention_mask"]),
        str(onnx_path),
        input_names=["input_ids", "attention_mask"],
        output_names=["embeddings"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "seq"},
            "attention_mask": {0: "batch", 1: "seq"},
            "embeddings": {0: "batch"},
        },
        opset_version=14,
        do_constant_folding=True,
    )

    # Parity check against onnxruntime.
    import onnxruntime as ort

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    onnx_out = sess.run(
        None,
        {
            "input_ids": enc["input_ids"].numpy(),
            "attention_mask": enc["attention_mask"].numpy(),
        },
    )[0]
    with torch.no_grad():
        torch_out = encoder(enc["input_ids"], enc["attention_mask"]).numpy()

    max_diff = float(np.abs(onnx_out - torch_out).max())
    size_mb = onnx_path.stat().st_size / (1024 * 1024)
    print(f"Exported {onnx_path} ({size_mb:.1f} MB)")
    print(f"Parity max abs diff vs torch: {max_diff:.2e}")
    if max_diff > 1e-3:
        raise SystemExit("Parity check failed (diff too large)")

    if args.int8:
        from onnxruntime.quantization import QuantType, quantize_dynamic

        int8_path = onnx_path.with_name(onnx_path.stem + "-int8.onnx")
        quantize_dynamic(str(onnx_path), str(int8_path), weight_type=QuantType.QInt8)
        int8_mb = int8_path.stat().st_size / (1024 * 1024)
        print(f"Quantized int8 -> {int8_path} ({int8_mb:.1f} MB)")
    print("OK")


if __name__ == "__main__":
    main()
