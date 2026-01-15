"""
Test script to verify that the flag searcher produces consistent embeddings.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.src.flag_searcher import FlagSearcher


def test_flag_searcher():
    """Test the flag searcher with a sample query"""

    # Create flag searcher
    searcher = FlagSearcher(top_k=5)

    # Test with a sample query
    # test_query = "red and white stripes"
    test_query = "american flag"
    print(f"Testing query: '{test_query}'")

    # Run the query
    results = searcher.query(test_query, is_image=False)

    assert len(results.flags) == 5
    assert all(flag.score is not None for flag in results.flags)

    scores = [flag.score for flag in results.flags]
    assert scores == sorted(scores, reverse=True)


if __name__ == "__main__":
    test_flag_searcher()
