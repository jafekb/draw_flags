"""
Lexical name-match scoring shared by the eval hybrid and the deployed searcher, so
both rank identically.

A flag's meaningful name tokens (generic words like "flag"/"of"/"variant" removed)
are compared to the query tokens: full containment scores 1.0, partial overlap
scores proportionally. This is what lets "the flag of japan" surface the flag named
"Japan" even though the query is weak signal for the dense description embedding.
"""

from __future__ import annotations

from typing import List

import numpy as np

from backend.common.normalize import normalize_name

_STOP = {"flag", "of", "the", "a", "an", "and", "national", "state", "variant"}


def name_tokens(name: str) -> set:
    return {t for t in normalize_name(name).split() if t not in _STOP and len(t) > 1}


def build_name_token_sets(names: List[str]) -> List[set]:
    return [name_tokens(n) for n in names]


def name_overlap_scores(query: str, name_token_sets: List[set]) -> np.ndarray:
    query_tokens = set(normalize_name(query).split())
    scores = np.zeros(len(name_token_sets), dtype=np.float32)
    for i, toks in enumerate(name_token_sets):
        if not toks:
            continue
        if toks <= query_tokens:  # all meaningful name tokens present in query
            scores[i] = 1.0
        else:
            scores[i] = len(toks & query_tokens) / len(toks)
    return scores
