"""
Metrics harness for description->flag retrieval.

Every experiment implements `Experiment.rank(queries, top_k) -> list[list[str]]`,
returning ranked flag *names* per query. Matching against ground truth is by
normalized name (see backend/eval/normalize.py); a query is a hit at rank r if any
`expected` name appears at position r (1-indexed) in the returned list.

Reports Recall@1/5/10 and MRR@10, overall and per tier, and writes a per-query
results file so failures can be inspected.

Usage:
    uv run backend/eval/run_eval.py --experiment baseline
    uv run backend/eval/run_eval.py --compare
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, Dict, List, Protocol

import numpy as np

from backend.common.flag_data import flaglist_from_json
from backend.eval.normalize import normalize_name

QUERIES_FILE = Path("backend/eval/queries.json")
FLAGS_FILE = Path("backend/data/all_flags/flags.json")
RESULTS_DIR = Path("backend/eval/results")
K_VALUES = (1, 5, 10)
DEFAULT_TOP_K = 10


def load_queries() -> List[dict]:
    with QUERIES_FILE.open() as f:
        return json.load(f)["queries"]


def load_flag_names() -> List[str]:
    """Flag names in dataset order (index-aligned with embeddings.npy rows)."""
    return [flag.name for flag in flaglist_from_json(FLAGS_FILE).flags]


class Experiment(Protocol):
    name: str

    def rank(self, queries: List[str], top_k: int) -> List[List[str]]:
        """Return, for each query, the ranked list of flag names (best first)."""


class ClipBaselineExperiment:
    """Current production path: ONNX CLIP text encoder + precomputed image embeddings."""

    name = "baseline_clip_vitb32"

    def __init__(self) -> None:
        from backend.src.flag_searcher import FlagSearcher

        self._searcher = FlagSearcher(top_k=DEFAULT_TOP_K)

    def rank(self, queries: List[str], top_k: int) -> List[List[str]]:
        ranked = []
        for q in queries:
            result = self._searcher.query(q, is_image=False, top_k=top_k)
            ranked.append([f.name for f in result.flags])
        return ranked


class EmbeddingExperiment:
    """
    Generic same-index experiment: cosine search of query embeddings against a
    precomputed corpus matrix whose rows are aligned with dataset flag order.

    Used by future experiments (SigLIP, text-description embedders, etc.) — they
    supply a corpus matrix and a query-encoder callable; ranking logic is shared.
    """

    def __init__(
        self,
        name: str,
        corpus_embeddings: np.ndarray,
        encode_queries: Callable[[List[str]], np.ndarray],
        flag_names: List[str],
    ) -> None:
        self.name = name
        self._flag_names = flag_names
        self._encode_queries = encode_queries
        corpus = np.asarray(corpus_embeddings, dtype=np.float32)
        self._corpus = corpus / np.clip(np.linalg.norm(corpus, axis=1, keepdims=True), 1e-12, None)

    def rank(self, queries: List[str], top_k: int) -> List[List[str]]:
        q = np.asarray(self._encode_queries(queries), dtype=np.float32)
        q = q / np.clip(np.linalg.norm(q, axis=1, keepdims=True), 1e-12, None)
        sims = q @ self._corpus.T  # (num_queries, num_flags)
        ranked = []
        for row in sims:
            top_idx = np.argsort(-row)[:top_k]
            ranked.append([self._flag_names[i] for i in top_idx])
        return ranked


def _textdesc(model_name: str, *, include_name: bool):
    def factory():
        from backend.eval.embedders.text_description import make_text_description_experiment

        return make_text_description_experiment(model_name, include_name=include_name)

    return factory


def _image_clip(model_name: str):
    def factory():
        from backend.eval.embedders.image_clip import make_sentence_transformers_clip

        return make_sentence_transformers_clip(model_name)

    return factory


def _hybrid(model_name: str, weight: float, *, include_name_in_doc: bool):
    def factory():
        from backend.eval.embedders.hybrid import HybridExperiment

        return HybridExperiment(model_name, weight, include_name_in_doc=include_name_in_doc)

    return factory


# Registry of runnable experiments (name -> zero-arg factory). Add new experiments
# here as they are built; heavy imports stay lazy inside the factory.
EXPERIMENTS: Dict[str, Callable[[], Experiment]] = {
    "baseline": ClipBaselineExperiment,
    "textdesc_bge_small": _textdesc("BAAI/bge-small-en-v1.5", include_name=True),
    "textdesc_bge_small_desconly": _textdesc("BAAI/bge-small-en-v1.5", include_name=False),
    "textdesc_minilm": _textdesc("sentence-transformers/all-MiniLM-L6-v2", include_name=True),
    "textdesc_bge_base": _textdesc("BAAI/bge-base-en-v1.5", include_name=True),
    "image_clip_vitb32": _image_clip("clip-ViT-B-32"),
    "image_clip_vitl14": _image_clip("clip-ViT-L-14"),
    "hybrid_bge_base_w03": _hybrid("BAAI/bge-base-en-v1.5", 0.3, include_name_in_doc=False),
    "hybrid_bge_base_w05": _hybrid("BAAI/bge-base-en-v1.5", 0.5, include_name_in_doc=False),
    "hybrid_bge_small_w05": _hybrid("BAAI/bge-small-en-v1.5", 0.5, include_name_in_doc=False),
}


def _hit_rank(returned: List[str], expected_norm: set) -> int | None:
    for rank, name in enumerate(returned, start=1):
        if normalize_name(name) in expected_norm:
            return rank
    return None


def _aggregate(records: List[dict]) -> dict:
    if not records:
        return {f"recall@{k}": 0.0 for k in K_VALUES} | {"mrr@10": 0.0, "n": 0}
    metrics = {}
    for k in K_VALUES:
        metrics[f"recall@{k}"] = sum(
            1 for r in records if r["hit_rank"] is not None and r["hit_rank"] <= k
        ) / len(records)
    metrics["mrr@10"] = sum(
        (1.0 / r["hit_rank"]) if r["hit_rank"] is not None and r["hit_rank"] <= 10 else 0.0
        for r in records
    ) / len(records)
    metrics["n"] = len(records)
    return metrics


def compute_metrics(experiment_name: str, queries: List[dict], ranked: List[List[str]]) -> dict:
    per_query = []
    for q, returned in zip(queries, ranked):
        expected_norm = {normalize_name(e) for e in q["expected"]}
        rank = _hit_rank(returned, expected_norm)
        per_query.append(
            {
                "query": q["query"],
                "tier": q["tier"],
                "expected": q["expected"],
                "returned": returned,
                "hit_rank": rank,
            }
        )

    by_tier = {}
    for tier in ("easy", "medium", "hard"):
        by_tier[tier] = _aggregate([r for r in per_query if r["tier"] == tier])

    return {
        "experiment": experiment_name,
        "top_k": DEFAULT_TOP_K,
        "num_queries": len(queries),
        "overall": _aggregate(per_query),
        "by_tier": by_tier,
        "per_query": per_query,
    }


def _fmt_row(label: str, m: dict) -> str:
    return (
        f"  {label:<10} n={m['n']:<4} "
        f"R@1={m['recall@1']:.3f}  R@5={m['recall@5']:.3f}  "
        f"R@10={m['recall@10']:.3f}  MRR@10={m['mrr@10']:.3f}"
    )


def print_report(metrics: dict) -> None:
    print(f"\n=== {metrics['experiment']} ({metrics['num_queries']} queries) ===")
    print(_fmt_row("OVERALL", metrics["overall"]))
    for tier in ("easy", "medium", "hard"):
        print(_fmt_row(tier, metrics["by_tier"][tier]))


def run_experiment(name: str) -> dict:
    if name not in EXPERIMENTS:
        raise SystemExit(f"Unknown experiment {name!r}. Known: {sorted(EXPERIMENTS)}")
    queries = load_queries()
    experiment = EXPERIMENTS[name]()
    ranked = experiment.rank([q["query"] for q in queries], DEFAULT_TOP_K)
    metrics = compute_metrics(experiment.name, queries, ranked)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"{experiment.name}.json"
    with out.open("w") as f:
        json.dump(metrics, f, indent=2)
    print_report(metrics)
    print(f"\nWrote {out}")
    return metrics


def compare() -> None:
    files = sorted(RESULTS_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"No result files in {RESULTS_DIR}")
    rows = []
    for fp in files:
        with fp.open() as f:
            m = json.load(f)
        rows.append(m)
    header = f"{'experiment':<28} {'R@1':>6} {'R@5':>6} {'R@10':>6} {'MRR@10':>7}"
    print(header)
    print("-" * len(header))
    for m in sorted(rows, key=lambda x: x["overall"]["mrr@10"], reverse=True):
        o = m["overall"]
        print(
            f"{m['experiment']:<28} {o['recall@1']:>6.3f} {o['recall@5']:>6.3f} "
            f"{o['recall@10']:>6.3f} {o['mrr@10']:>7.3f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Flag retrieval eval harness")
    parser.add_argument("--experiment", help="Experiment name to run", default=None)
    parser.add_argument("--compare", action="store_true", help="Compare all saved results")
    args = parser.parse_args()

    if args.compare:
        compare()
    elif args.experiment:
        run_experiment(args.experiment)
    else:
        parser.error("pass --experiment <name> or --compare")


if __name__ == "__main__":
    main()
