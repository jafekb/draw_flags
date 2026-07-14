# Improving flag search quality

## Problem

The deployed text→flag search worked poorly for *descriptive* queries (e.g. "green
flag with a white crescent and star"). The production path embeds the query with a
`clip-ViT-B-32` text encoder and matches it against precomputed flag **image**
embeddings — a cross-modal comparison. Flags are abstract and out-of-distribution
for CLIP, and ViT-B/32 is the weakest variant, so descriptive queries barely align.
Name queries ("flag of Japan") worked passably; anything visual did not.

Example (baseline, top-5 for "green and white with crescent moon"): Surnadal,
Chechnya, Øyer, Kingdom of Egypt, Libya — Pakistan not in the top 5.

## Method: a measurable eval

Before changing anything we built a **validated eval set** and a metrics harness so
quality is a number, not a vibe.

- `backend/eval/queries.json`: 132 description→flag queries in three tiers —
  **easy** (name/near-name, 30), **medium** (color + layout, 43), **hard** (fine
  emblems / vexillology, 59). Ground truth is matched by *normalized* flag name so
  dataset variants ("Bangladesh (variant 2)", "Russia (GOST …)") match a clean
  expected name; a query is a hit if any accepted answer appears in top-k.
- `backend/eval/run_eval.py`: pluggable experiments reporting **Recall@1/5/10** and
  **MRR@10**, overall and per tier, with per-query dumps and a `--compare` mode.
- `backend/eval/validate_queries.py` + `test_eval_set.py`: guarantee every query is
  answerable against the real dataset (guards against rot).

## Baseline (clip-ViT-B-32, current production path)

| Tier | R@1 | R@5 | R@10 | MRR@10 |
|------|-----|-----|------|--------|
| Overall | 0.182 | 0.326 | 0.424 | 0.252 |
| easy | 0.533 | 0.800 | 0.967 | 0.674 |
| medium | 0.070 | 0.140 | 0.209 | 0.104 |
| hard | 0.085 | 0.220 | 0.305 | 0.146 |

Name queries half-work; descriptive queries are near-broken (R@1 ≈ 0.07–0.09).

## Approach: text-to-text retrieval via VLM descriptions

Key insight: stop doing cross-modal retrieval. Generate a vivid, **country-agnostic
visual description** of each flag once (colors, layout, emblems) with a vision model,
embed those descriptions with a strong **text** embedder, and match the query in the
*same* modality. "green and white with crescent moon" then matches a stored
description "green field with a white crescent and star" directly.

- Descriptions are generated offline (`backend/scripts/generate_descriptions.py`,
  Claude vision) and stored in `backend/data/all_flags/descriptions.json`. The prompt
  forbids naming the country, forcing genuinely visual vocabulary.
- The deployed query-time model stays small (a sentence-transformer text encoder),
  which fits the Render Starter 512 MB budget — corpus embeddings are precomputed.

## Results

Head-to-head on the 132-query eval (overall, best variant per family). Descriptions
cover national/organization/historical flags; the long tail stays name-only (still
findable by the name-match term).

| Experiment | R@1 | R@5 | R@10 | MRR@10 |
|---|---|---|---|---|
| baseline CLIP ViT-B/32 (production) | 0.182 | 0.326 | 0.424 | 0.252 |
| text-desc, MiniLM (name+desc) | 0.356 | 0.591 | 0.705 | 0.460 |
| text-desc, bge-small (name+desc) | 0.455 | 0.712 | 0.841 | 0.569 |
| text-desc, bge-base (name+desc) | 0.492 | 0.803 | 0.841 | 0.604 |
| **hybrid, bge-base + name-match (w=0.3)** | **0.667** | **0.864** | **0.894** | **0.753** |

Per-tier for the winner (hybrid bge-base, w=0.3):

| Tier | R@1 | R@5 | R@10 | MRR@10 |
|------|-----|-----|------|--------|
| easy | 0.767 | 0.967 | 0.967 | 0.867 |
| medium | 0.674 | 0.860 | 0.907 | 0.754 |
| hard | 0.610 | 0.814 | 0.847 | 0.695 |

### What moved the needle

1. **Same-modality retrieval** (text query → text description) instead of cross-modal
   is the core win: medium R@1 went 0.070 → 0.60+, hard 0.085 → 0.61.
2. **BGE query instruction prefix** — BGE v1.5 expects a query-side instruction;
   adding it lifted bge-small MRR 0.500 → 0.569.
3. **Hybrid name-match term** — pure description embedding regressed *name* queries
   (a name is weak signal against a visually-rich doc). Adding a lexical name-overlap
   boost recovered easy-tier (R@1 0.07 → 0.77) with no loss on descriptive tiers.
   Weight 0.3 was the sweet spot; higher weights max name queries but slightly dent
   the hard tier.
4. **bge-base > bge-small > MiniLM** on quality; deploy trades this against the
   512 MB / 0.5 CPU Render budget (see deployment note).

Net: **MRR 0.252 → 0.753 (≈3×), R@1 0.182 → 0.667 (≈3.7×)**, and the qualitative
failure is fixed — "green and white with crescent moon" now returns Pakistan at the
top instead of an obscure Norwegian municipality.

## Reproduce

```bash
./scripts/setup-env.sh dev
uv run backend/scripts/download_images.py            # fetch flag images (polite/resumable)
uv run backend/scripts/generate_descriptions.py      # VLM descriptions (needs ANTHROPIC_API_KEY)
uv run backend/eval/run_eval.py --experiment baseline
uv run backend/eval/run_eval.py --experiment textdesc_bge_small
uv run backend/eval/run_eval.py --compare
```
