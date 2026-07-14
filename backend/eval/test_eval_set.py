"""
Pytest guard so the eval set can't silently rot.

Verifies queries.json is well-formed and every query is answerable against the
current dataset (at least one expected name resolves to a real flag).
"""

from backend.eval.validate_queries import validate


def test_eval_set_is_valid():
    assert validate() == 0, "eval query set failed validation (see stdout)"
