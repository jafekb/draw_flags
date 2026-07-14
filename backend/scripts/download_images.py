#!/usr/bin/env python3
"""
Download flag images referenced by flags.json into a local directory and convert
SVGs to PNG. Resumable (skips files that already exist) and polite to Wikimedia
(proper User-Agent, modest concurrency).

Filenames use the same _safe_name convention as
generate_embeddings_from_images.py so downstream embedding scripts line up.

Usage:
    uv run backend/scripts/download_images.py
    uv run backend/scripts/download_images.py --limit 237 --categories national
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import requests

from backend.common.flag_data import flaglist_from_json

FLAGS_FILE = Path("backend/data/all_flags/flags.json")
IMAGES_DIR = Path("backend/data/all_flags/images")
USER_AGENT = "DrawFlags/0.1 (https://github.com/jafekb/draw_flags; jafek91@gmail.com)"


def safe_name(name: str) -> str:
    cleaned = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()
    return cleaned.replace(" ", "_")


def _ext_from_url(url: str) -> str:
    low = url.lower()
    for ext in (".svg", ".png", ".jpg", ".jpeg", ".gif"):
        if low.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".png"


def _target_path(name: str, url: str) -> Path:
    return IMAGES_DIR / f"{safe_name(name)}{_ext_from_url(url)}"


def download_one(name: str, url: str, max_retries: int = 5) -> tuple[str, str]:
    dest = _target_path(name, url)
    if dest.exists() and dest.stat().st_size > 0:
        return ("skip", name)
    backoff = 2.0
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            if resp.status_code == 429:
                wait = float(resp.headers.get("retry-after", backoff))
                time.sleep(wait)
                backoff = min(backoff * 2, 60)
                continue
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return ("ok", name)
        except requests.exceptions.RequestException as exc:
            if attempt == max_retries - 1:
                return ("fail", f"{name}: {exc}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
    return ("fail", f"{name}: exhausted retries")


def convert_svgs() -> int:
    try:
        import cairosvg
    except ImportError:
        print("cairosvg not installed; skipping SVG->PNG conversion")
        return 0
    converted = 0
    for svg in IMAGES_DIR.glob("*.svg"):
        png = svg.with_suffix(".png")
        if png.exists() and png.stat().st_size > 0:
            continue
        try:
            cairosvg.svg2png(bytestring=svg.read_bytes(), write_to=str(png))
            converted += 1
        except Exception as exc:
            print(f"  SVG convert failed {svg.name}: {exc}")
    return converted


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--categories", nargs="*", default=None, help="Filter by flag category")
    ap.add_argument("--delay", type=float, default=0.7, help="Seconds between requests (polite)")
    args = ap.parse_args()

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    flags = flaglist_from_json(FLAGS_FILE).flags
    if args.categories:
        flags = [f for f in flags if f.category in set(args.categories)]
    if args.limit:
        flags = flags[: args.limit]

    print(f"Downloading {len(flags)} images sequentially (delay={args.delay}s) -> {IMAGES_DIR}")
    counts = {"ok": 0, "skip": 0, "fail": 0}
    failures = []
    for i, f in enumerate(flags, 1):
        status, info = download_one(f.name, f.wikipedia_image_url)
        counts[status] += 1
        if status == "fail":
            failures.append(info)
        if status == "ok":
            time.sleep(args.delay)  # only pause after a real network hit
        if i % 100 == 0:
            print(
                f"  {i}/{len(flags)}  ok={counts['ok']} skip={counts['skip']} "
                f"fail={counts['fail']}",
                flush=True,
            )

    print(f"Downloaded ok={counts['ok']} skip={counts['skip']} fail={counts['fail']}")
    if failures:
        print(f"First failures ({min(10, len(failures))} of {len(failures)}):")
        for f in failures[:10]:
            print("  -", f)

    print("Converting SVGs to PNG...")
    n = convert_svgs()
    print(f"Converted {n} SVGs. Done.")


if __name__ == "__main__":
    main()
