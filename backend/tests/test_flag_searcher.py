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
    searcher = FlagSearcher(top_k=10)

    test_cases = [
        ("american flag", "United States"),
        ("united states of america", "United States"),
        ("ukraine", "Ukraine"),
        ("democractic republic of congo", "Democratic Republic of the Congo"),
    ]

    for query, expected in test_cases:
        print(f"Testing query: '{query}'")
        results = searcher.query(query, is_image=False, top_k=10)

        assert len(results.flags) == 10
        assert all(flag.score is not None for flag in results.flags)

        scores = [flag.score for flag in results.flags]
        assert scores == sorted(scores, reverse=True)

        names = [flag.name for flag in results.flags]
        assert expected in names


if __name__ == "__main__":
    test_flag_searcher()
