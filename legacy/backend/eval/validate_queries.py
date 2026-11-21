"""
Validate the eval query set against the flag dataset.

Ensures every query is answerable: each query must have at least one `expected`
name that resolves (by normalized form) to a real flag in flags.json. Individual
expected names that are absent are warned about (useful for cleanup) but only a
query with ZERO resolvable expected names is a hard error.

Usage:
    uv run backend/eval/validate_queries.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

from backend.common.flag_data import flaglist_from_json
from backend.common.normalize import normalize_name

QUERIES_FILE = Path("backend/eval/queries.json")
FLAGS_FILE = Path("backend/data/all_flags/flags.json")
ALLOWED_TIERS = {"easy", "medium", "hard"}


def load_queries() -> list:
    with QUERIES_FILE.open() as f:
        return json.load(f)["queries"]


def dataset_normalized_names() -> set:
    flags = flaglist_from_json(FLAGS_FILE)
    return {normalize_name(flag.name) for flag in flags.flags}


def validate() -> int:
    queries = load_queries()
    present = dataset_normalized_names()

    errors: list[str] = []
    warnings: list[str] = []
    seen_queries: Counter = Counter()

    for i, q in enumerate(queries):
        qtext = q.get("query", "")
        seen_queries[qtext] += 1

        if not qtext:
            errors.append(f"[{i}] empty query text")
        if q.get("tier") not in ALLOWED_TIERS:
            errors.append(f"[{i}] {qtext!r}: bad tier {q.get('tier')!r}")

        expected = q.get("expected") or []
        if not expected:
            errors.append(f"[{i}] {qtext!r}: empty expected list")
            continue

        resolvable = [e for e in expected if normalize_name(e) in present]
        missing = [e for e in expected if normalize_name(e) not in present]
        if missing:
            warnings.append(f"[{i}] {qtext!r}: expected not in dataset: {missing}")
        if not resolvable:
            errors.append(f"[{i}] {qtext!r}: NO expected name resolves to a real flag: {expected}")

    for qtext, count in seen_queries.items():
        if count > 1:
            errors.append(f"duplicate query ({count}x): {qtext!r}")

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print("  -", w)
        print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print("  -", e)
        print(f"\nFAILED: {len(errors)} error(s) across {len(queries)} queries.")
        return 1

    print(f"OK: {len(queries)} queries valid ({len(warnings)} soft warnings).")
    return 0


if __name__ == "__main__":
    sys.exit(validate())
