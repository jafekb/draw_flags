"""
Debug script to understand the structure of the sentence-transformers CLIP model.
"""

from sentence_transformers import SentenceTransformer


def debug_model_structure():
    """Debug the model structure"""
    
    # Load the sentence-transformers CLIP model
    st_model = SentenceTransformer("clip-ViT-B-32")
    
    print("Model structure:")
    print(f"Type: {type(st_model)}")
    print(f"Modules: {list(st_model.modules())}")
    
    first_module = st_model._first_module()
    print(f"\nFirst module type: {type(first_module)}")
    print(f"First module attributes: {dir(first_module)}")
    
    # Try to find the text model
    if hasattr(first_module, "text_model"):
        print("Found text_model attribute")
    elif hasattr(first_module, "text"):
        print("Found text attribute")
    elif hasattr(first_module, "text_encoder"):
        print("Found text_encoder attribute")
    else:
        print("No text model found in expected attributes")
        print(f"Available attributes: {[attr for attr in dir(first_module) if not attr.startswith('_')]}")

if __name__ == "__main__":
    debug_model_structure() 