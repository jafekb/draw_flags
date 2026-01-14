"""
Minimal tokenizer implementation using just the tokenizers library
to replace the heavy transformers dependency.
"""

import numpy as np
from tokenizers import Tokenizer


class MinimalCLIPTokenizer:
    """Minimal CLIP tokenizer implementation (matches CLIPTokenizer behavior)."""

    max_length = 77
    bos_token = "<|startoftext|>"
    eos_token = "<|endoftext|>"

    def __init__(self):
        # Load the CLIP tokenizer from the tokenizers library
        # We'll need to download the tokenizer files
        self.tokenizer = Tokenizer.from_pretrained("openai/clip-vit-base-patch32")
        self.bos_token_id = self.tokenizer.token_to_id(self.bos_token)
        self.eos_token_id = self.tokenizer.token_to_id(self.eos_token)

        if self.bos_token_id is None or self.eos_token_id is None:
            raise ValueError("CLIP tokenizer missing BOS/EOS tokens")

    def _encode(self, text):
        # Encode with special tokens if the tokenizer supports it
        try:
            encoding = self.tokenizer.encode(text, add_special_tokens=True)
            ids = list(encoding.ids)
        except TypeError:
            encoding = self.tokenizer.encode(text)
            ids = list(encoding.ids)

        # Ensure BOS/EOS are present
        if not ids or ids[0] != self.bos_token_id:
            ids = [self.bos_token_id] + ids
        if ids[-1] != self.eos_token_id:
            ids = ids + [self.eos_token_id]

        # Truncate to max length (keep EOS at end)
        if len(ids) > self.max_length:
            ids = ids[: self.max_length]
            ids[-1] = self.eos_token_id

        # Pad to max length using EOS token (CLIP pad_token == eos_token)
        attention_mask = [1] * len(ids)
        if len(ids) < self.max_length:
            pad_len = self.max_length - len(ids)
            ids = ids + [self.eos_token_id] * pad_len
            attention_mask = attention_mask + [0] * pad_len

        return ids, attention_mask

    def __call__(self, text, return_tensors="np", padding=True, truncation=True):
        """Tokenize text similar to transformers CLIPTokenizer."""
        ids, attention_mask = self._encode(text)
        input_ids = np.array([ids])
        attention_mask = np.array([attention_mask])
        return {"input_ids": input_ids, "attention_mask": attention_mask}


def create_minimal_tokenizer():
    """Create a minimal tokenizer that mimics CLIPTokenizer behavior"""
    try:
        return MinimalCLIPTokenizer()
    except Exception as e:
        print(f"Warning: Could not create minimal tokenizer: {e}")
        print("Falling back to transformers CLIPTokenizer")
        from transformers import CLIPTokenizer

        return CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32")
