#!/usr/bin/env python3
"""
Test script to verify ONNX model works correctly.
"""

import numpy as np
from pathlib import Path
import onnxruntime as ort
from transformers import CLIPTokenizer

def test_onnx_model():
    """Test the ONNX model with a sample query"""
    
    model_path = Path("backend/models/clip-text-encoder.onnx")
    if not model_path.exists():
        print("ONNX model not found. Please run convert_to_onnx.py first.")
        return
    
    # Load the model and tokenizer
    session = ort.InferenceSession(str(model_path), providers=['CPUExecutionProvider'])
    tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32")
    
    # Test with sample queries
    test_queries = [
        "red and white stripes",
        "blue background with stars",
        "green and yellow flag"
    ]
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        
        # Tokenize input
        inputs = tokenizer(query, return_tensors="np", padding=True, truncation=True)
        
        # Run inference
        outputs = session.run(None, {
            'input_ids': inputs['input_ids'],
            'attention_mask': inputs['attention_mask']
        })
        
        # Get embeddings and normalize
        embeddings = outputs[0]
        normalized_embeddings = embeddings / np.linalg.norm(embeddings, axis=-1, keepdims=True)
        
        print(f"Embedding shape: {normalized_embeddings.shape}")
        print(f"Embedding norm: {np.linalg.norm(normalized_embeddings):.6f}")
    
    print("\nONNX model test completed successfully!")

if __name__ == "__main__":
    test_onnx_model() 