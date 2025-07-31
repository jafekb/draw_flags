#!/usr/bin/env python3
"""
Convert CLIP text encoder to ONNX format for smaller deployment size.
This script extracts the text encoder from sentence-transformers CLIP and converts it to ONNX.
"""

import torch
import onnx
import onnxruntime as ort
from sentence_transformers import SentenceTransformer
from transformers import CLIPTokenizer
from pathlib import Path

def convert_clip_to_onnx():
    """Convert CLIP text encoder to ONNX format"""
    
    # Create models directory
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    # Load the sentence-transformers CLIP model
    st_model = SentenceTransformer("clip-ViT-B-32")
    
    # Extract the text model from sentence-transformers
    text_model = st_model._first_module().model.text_model
    text_model.eval()
    
    # Get the tokenizer
    tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32")
    
    # Create dummy input for ONNX export
    dummy_text = "red and white stripes"
    inputs = tokenizer(dummy_text, return_tensors="pt", padding=True, truncation=True)
    
    # Export to ONNX
    onnx_path = models_dir / "clip-text-encoder.onnx"
    
    torch.onnx.export(
        text_model,
        (inputs['input_ids'], inputs['attention_mask']),
        onnx_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input_ids', 'attention_mask'],
        output_names=['last_hidden_state'],
        dynamic_axes={
            'input_ids': {0: 'batch_size', 1: 'sequence_length'},
            'attention_mask': {0: 'batch_size', 1: 'sequence_length'},
            'last_hidden_state': {0: 'batch_size', 1: 'sequence_length'}
        }
    )
    
    print(f"ONNX model saved to {onnx_path}")
    
    # Test the ONNX model
    session = ort.InferenceSession(str(onnx_path), providers=['CPUExecutionProvider'])
    
    # Test with a sample input
    test_text = "red and white stripes"
    test_inputs = tokenizer(test_text, return_tensors="np", padding=True, truncation=True)
    
    outputs = session.run(None, {
        'input_ids': test_inputs['input_ids'],
        'attention_mask': test_inputs['attention_mask']
    })
    
    print(f"ONNX model test successful! Output shape: {outputs[0].shape}")
    print(f"Model size: {onnx_path.stat().st_size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    convert_clip_to_onnx() 
