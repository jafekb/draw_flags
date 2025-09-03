"""
Minimal tokenizer implementation using just the tokenizers library
to replace the heavy transformers dependency.
"""


import numpy as np
from tokenizers import Tokenizer


class MinimalCLIPTokenizer:
    """Minimal CLIP tokenizer implementation"""
    
    def __init__(self):
        # Load the CLIP tokenizer from the tokenizers library
        # We'll need to download the tokenizer files
        self.tokenizer = Tokenizer.from_pretrained("openai/clip-vit-base-patch32")
    
    def __call__(self, text, return_tensors="np", padding=True, truncation=True):
        """Tokenize text similar to transformers CLIPTokenizer"""
        
        # Tokenize the text
        encoding = self.tokenizer.encode(text)
        
        # Get input_ids and attention_mask
        input_ids = np.array([encoding.ids])
        attention_mask = np.array([encoding.attention_mask])
        
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask
        }


def create_minimal_tokenizer():
    """Create a minimal tokenizer that mimics CLIPTokenizer behavior"""
    try:
        return MinimalCLIPTokenizer()
    except Exception as e:
        print(f"Warning: Could not create minimal tokenizer: {e}")
        print("Falling back to transformers CLIPTokenizer")
        from transformers import CLIPTokenizer
        return CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32") 