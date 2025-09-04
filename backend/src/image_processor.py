"""
Lightweight image processor for CLIP embeddings using transformers library only.
Avoids heavy sentence-transformers dependencies while maintaining identical quality.
"""

from io import BytesIO

import numpy as np

# Global variables to cache the model components once loaded
_clip_model = None
_clip_processor = None


def _get_clip_components():
    """Lazy-load the CLIP model and processor only when needed"""
    global _clip_model, _clip_processor

    if _clip_model is None or _clip_processor is None:
        # Use transformers library directly (much lighter than sentence-transformers)
        from transformers import CLIPModel, CLIPProcessor

        print("Loading CLIP image model (first time only)...")
        _clip_model = CLIPModel.from_pretrained(
            "openai/clip-vit-base-patch32", use_safetensors=True
        )
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        print("✅ CLIP image model loaded")

    return _clip_model, _clip_processor


def encode_image(image_data: BytesIO) -> np.ndarray:
    """
    Encode an image into a CLIP embedding using transformers library only

    Args:
        image_data: BytesIO object containing image bytes (PNG, JPEG, etc.)

    Returns:
        Normalized CLIP embedding as numpy array (same quality as sentence-transformers)
    """
    import torch
    from PIL import Image

    # Load image from bytes
    image_data.seek(0)  # Reset stream position
    image = Image.open(image_data).convert("RGB")

    # Get the lazy-loaded model components
    model, processor = _get_clip_components()

    # Process image with CLIP
    inputs = processor(images=image, return_tensors="pt")

    # Get image features (same as sentence-transformers does internally)
    with torch.no_grad():
        image_features = model.get_image_features(**inputs)

    # Normalize features (same as sentence-transformers)
    image_features = image_features / image_features.norm(dim=-1, keepdim=True)

    # Convert to numpy and return first (and only) embedding
    embedding = image_features.detach().numpy()
    return embedding[0]


def is_image_model_loaded() -> bool:
    """Check if the image model is already loaded in memory"""
    return _clip_model is not None
