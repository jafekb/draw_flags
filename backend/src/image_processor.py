"""
Lazy-loading image processor for CLIP embeddings.
Only imports sentence-transformers when actually needed for image processing.
"""

from io import BytesIO

import numpy as np

# Global variable to cache the model once loaded
_image_model = None


def _get_image_model():
    """Lazy-load the image model only when needed"""
    global _image_model

    if _image_model is None:
        # Only import sentence-transformers when actually needed
        from sentence_transformers import SentenceTransformer

        print("Loading CLIP image model (first time only)...")
        _image_model = SentenceTransformer("clip-ViT-B-32")
        print("✅ CLIP image model loaded")

    return _image_model


def encode_image(image_data: BytesIO) -> np.ndarray:
    """
    Encode an image into a CLIP embedding using lazy-loaded model

    Args:
        image_data: BytesIO object containing image bytes (PNG, JPEG, etc.)

    Returns:
        Normalized CLIP embedding as numpy array
    """
    from PIL import Image

    # Load image from bytes
    image_data.seek(0)  # Reset stream position
    image = Image.open(image_data).convert("RGB")

    # Get the lazy-loaded model
    model = _get_image_model()

    # Encode using the CLIP model
    # The encode method handles both text and images automatically
    embedding = model.encode([image])

    # Return the embedding (already normalized by sentence-transformers)
    return embedding[0]


def is_image_model_loaded() -> bool:
    """Check if the image model is already loaded in memory"""
    return _image_model is not None
