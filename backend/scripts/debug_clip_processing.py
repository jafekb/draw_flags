#!/usr/bin/env python3
"""
Debug script to understand how sentence-transformers processes CLIP embeddings
and compare with our ONNX approach.
"""

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from transformers import CLIPTokenizer


def debug_clip_processing():
    """Debug how sentence-transformers processes CLIP embeddings"""
    
    # Load the sentence-transformers model
    st_model = SentenceTransformer("clip-ViT-B-32")
    
    # Get the first module (CLIP module)
    clip_module = st_model._first_module()
    print(f"CLIP module type: {type(clip_module)}")
    print(f"CLIP module: {clip_module}")
    
    # Get the text model
    text_model = clip_module.model.text_model
    print(f"Text model type: {type(text_model)}")
    
    # Get the tokenizer
    tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-base-patch32")
    
    # Test text
    test_text = "red and white stripes"
    print(f"\nTesting with text: '{test_text}'")
    
    # Method 1: Use sentence-transformers directly
    st_embedding = st_model.encode([test_text])
    print(f"Sentence-transformers embedding shape: {st_embedding.shape}")
    print(f"Sentence-transformers embedding norm: {np.linalg.norm(st_embedding):.6f}")
    
    # Method 2: Use the raw CLIP text model
    inputs = tokenizer(test_text, return_tensors="pt", padding=True, truncation=True)
    
    with torch.no_grad():
        # Get the raw CLIP output
        clip_output = text_model(**inputs)
        last_hidden_state = clip_output.last_hidden_state
        print(f"Raw CLIP last_hidden_state shape: {last_hidden_state.shape}")
        
        # Try different pooling strategies
        attention_mask = inputs["attention_mask"]
        
        # Mean pooling (excluding padding)
        masked_embeddings = last_hidden_state * attention_mask.unsqueeze(-1)
        mean_pooled = masked_embeddings.sum(dim=1) / attention_mask.sum(dim=1, keepdim=True)
        print(f"Mean pooled shape: {mean_pooled.shape}")
        print(f"Mean pooled norm: {torch.norm(mean_pooled):.6f}")
        
        # Use the EOS token embedding (last non-padded token)
        eos_positions = attention_mask.sum(dim=1) - 1
        eos_embeddings = last_hidden_state[torch.arange(last_hidden_state.size(0)), eos_positions]
        print(f"EOS token embedding shape: {eos_embeddings.shape}")
        print(f"EOS token embedding norm: {torch.norm(eos_embeddings):.6f}")
        
        # Try using the CLS token (first token)
        cls_embeddings = last_hidden_state[:, 0, :]
        print(f"CLS token embedding shape: {cls_embeddings.shape}")
        print(f"CLS token embedding norm: {torch.norm(cls_embeddings):.6f}")
    
    # Compare similarities
    st_embedding_tensor = torch.from_numpy(st_embedding)
    
    print("\nCosine similarities:")
    print(f"ST vs Mean pooled: {torch.cosine_similarity(st_embedding_tensor, mean_pooled, dim=1).item():.6f}")
    print(f"ST vs EOS token: {torch.cosine_similarity(st_embedding_tensor, eos_embeddings, dim=1).item():.6f}")
    print(f"ST vs CLS token: {torch.cosine_similarity(st_embedding_tensor, cls_embeddings, dim=1).item():.6f}")
    
    # Check if sentence-transformers applies any additional processing
    print("\nChecking if ST applies additional processing...")
    
    # Let's look at the CLIP module's forward method
    print(f"CLIP module forward method: {clip_module.forward}")
    
    # Let's also check what the sentence-transformers CLIP model does
    print("\nChecking sentence-transformers CLIP model structure...")
    print(f"CLIP model attributes: {[attr for attr in dir(clip_module.model) if not attr.startswith('_')]}")
    
    # Try to understand the text projection
    if hasattr(clip_module.model, "text_projection"):
        text_projection = clip_module.model.text_projection
        print(f"Text projection type: {type(text_projection)}")
        print(f"Text projection weight shape: {text_projection.weight.shape}")
        
        # Apply text projection to our raw embeddings
        projected_mean = text_projection(mean_pooled)
        projected_eos = text_projection(eos_embeddings)
        projected_cls = text_projection(cls_embeddings)
        
        print(f"Projected mean norm: {torch.norm(projected_mean):.6f}")
        print(f"Projected EOS norm: {torch.norm(projected_eos):.6f}")
        print(f"Projected CLS norm: {torch.norm(projected_cls):.6f}")
        
        print(f"ST vs Projected mean: {torch.cosine_similarity(st_embedding_tensor, projected_mean, dim=1).item():.6f}")
        print(f"ST vs Projected EOS: {torch.cosine_similarity(st_embedding_tensor, projected_eos, dim=1).item():.6f}")
        print(f"ST vs Projected CLS: {torch.cosine_similarity(st_embedding_tensor, projected_cls, dim=1).item():.6f}")
    
    # Let's look at the actual CLIP model's text projection
    if hasattr(clip_module.model, "text_projection"):
        print(f"\nCLIP model text_projection shape: {clip_module.model.text_projection.weight.shape}")
        
        # Check if there's a text projection in the raw CLIP model
        if hasattr(text_model, "text_projection"):
            print(f"Raw text model text_projection shape: {text_model.text_projection.weight.shape}")
        else:
            print("Raw text model has no text_projection")
    
    # Let's try to understand how sentence-transformers processes the embeddings
    # by looking at the CLIP model's forward method
    print("\nExamining CLIP model forward method...")
    
    # Let's check if there's a text projection in the CLIP model
    clip_model = clip_module.model
    print(f"CLIP model type: {type(clip_model)}")
    
    # Check if the CLIP model has a text_projection
    if hasattr(clip_model, "text_projection"):
        print(f"CLIP model text_projection exists: {clip_model.text_projection.weight.shape}")
        
        # Try applying the projection to our raw embeddings
        # First, let's check if we need to normalize before projection
        normalized_mean = mean_pooled / torch.norm(mean_pooled, dim=-1, keepdim=True)
        normalized_eos = eos_embeddings / torch.norm(eos_embeddings, dim=-1, keepdim=True)
        normalized_cls = cls_embeddings / torch.norm(cls_embeddings, dim=-1, keepdim=True)
        
        projected_norm_mean = clip_model.text_projection(normalized_mean)
        projected_norm_eos = clip_model.text_projection(normalized_eos)
        projected_norm_cls = clip_model.text_projection(normalized_cls)
        
        print(f"ST vs Normalized+Projected mean: {torch.cosine_similarity(st_embedding_tensor, projected_norm_mean, dim=1).item():.6f}")
        print(f"ST vs Normalized+Projected EOS: {torch.cosine_similarity(st_embedding_tensor, projected_norm_eos, dim=1).item():.6f}")
        print(f"ST vs Normalized+Projected CLS: {torch.cosine_similarity(st_embedding_tensor, projected_norm_cls, dim=1).item():.6f}")

if __name__ == "__main__":
    debug_clip_processing() 