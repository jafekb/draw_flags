"""
Test script to verify that the flag searcher produces consistent embeddings.
"""

import sys
from io import BytesIO
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.src.flag_searcher import FlagSearcher


def test_text_search():
    """Test the flag searcher with a text query"""
    print("=== Testing Text Search ===")

    # Create flag searcher
    searcher = FlagSearcher(top_k=5)

    # Test with a sample query
    # test_query = "red and white stripes"
    test_query = "american flag"
    print(f"Testing query: '{test_query}'")

    # Run the query using the new API
    results = searcher.query(text_query=test_query)

    print(f"Found {len(results.flags)} flags")
    for i, flag in enumerate(results.flags):
        print(f"{i + 1}. {flag.name} (score: {flag.score:.4f})")
    print()


def test_image_search():
    """Test the flag searcher with an image query"""
    print("=== Testing Image Search ===")

    # Create flag searcher
    searcher = FlagSearcher(top_k=5)

    # Path to the test image
    image_path = Path("/home/bjafek/Downloads/flag_of_guyana.png")

    if not image_path.exists():
        print(f"❌ Test image not found at {image_path}")
        return

    print(f"Testing with image: {image_path}")

    # Read the image file
    with image_path.open("rb") as f:
        image_data = f.read()

    # Convert to BytesIO for the API
    image_bytes = BytesIO(image_data)

    # Run the image query
    results = searcher.query(image_data=image_bytes)

    print(f"Found {len(results.flags)} flags")
    for i, flag in enumerate(results.flags):
        print(f"{i + 1}. {flag.name} (score: {flag.score:.4f})")
    print()


if __name__ == "__main__":
    test_text_search()
    test_image_search()
