"""
CLIP image encoder for processing uploaded images.
This uses the same CLIP model as the text encoder to create embeddings in the same vector space.
"""

import numpy as np
from PIL import Image
from sentence_transformers import SentenceTransformer


class CLIPImageEncoder:
    """Encodes images using CLIP to create embeddings comparable with text embeddings"""

    def __init__(self):
        # Use the same CLIP model as we use for text
        self.model = SentenceTransformer("clip-ViT-B-32")

    def encode_image(self, image_data: bytes) -> np.ndarray:
        """
        Encode an image into a CLIP embedding

        Args:
            image_data: Raw image bytes (PNG, JPEG, etc.)

        Returns:
            Normalized CLIP embedding as numpy array
        """
        # Load image from bytes
        image = Image.open(image_data).convert("RGB")

        # Encode using the CLIP model
        # The encode method handles both text and images automatically
        embedding = self.model.encode([image])

        # Return the embedding (already normalized by sentence-transformers)
        return embedding[0]
