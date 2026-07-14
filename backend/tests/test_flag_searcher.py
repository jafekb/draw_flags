"""
Smoke test for the hybrid text-description FlagSearcher: both name queries and
visual-description queries should surface the right flag in the top results, and
scores should be sorted descending.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.src.flag_searcher import FlagSearcher


def test_flag_searcher():
    searcher = FlagSearcher(top_k=10)

    test_cases = [
        # name queries (handled by the lexical name-match term)
        ("the flag of Japan", "Japan"),
        ("Ukraine", "Ukraine"),
        # description queries (handled by dense description similarity)
        ("green flag with a white crescent moon and a star", "Pakistan"),
        ("a red circle centered on a white field", "Japan"),
        ("blue field with a yellow Scandinavian cross", "Sweden"),
    ]

    for query, expected in test_cases:
        results = searcher.query(query, is_image=False, top_k=10)

        assert len(results.flags) == 10
        assert all(flag.score is not None for flag in results.flags)

        scores = [flag.score for flag in results.flags]
        assert scores == sorted(scores, reverse=True)

        names = [flag.name for flag in results.flags]
        assert expected in names, f"{expected!r} not in top-10 for {query!r}: {names}"


if __name__ == "__main__":
    test_flag_searcher()
