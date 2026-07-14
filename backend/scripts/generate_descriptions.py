#!/usr/bin/env python3
"""
Generate country-agnostic visual descriptions of flag images with the Claude
vision API. Resumable: skips flags already present in descriptions.json.

Requires ANTHROPIC_API_KEY in the environment and the `anthropic` package
(`uv pip install anthropic`). Images must already be downloaded (see
download_images.py).

Usage:
    uv run backend/scripts/generate_descriptions.py
    uv run backend/scripts/generate_descriptions.py --limit 237 --categories national
    uv run backend/scripts/generate_descriptions.py --model claude-opus-4-8

The exact same prompt (backend/common/descriptions.VLM_PROMPT) is used whether
descriptions come from this script or are backfilled another way, so the store
stays consistent.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path

from backend.common.descriptions import (
    VLM_PROMPT,
    load_descriptions,
    save_descriptions,
)
from backend.common.flag_data import flaglist_from_json
from backend.scripts.download_images import IMAGES_DIR, safe_name

FLAGS_FILE = Path("backend/data/all_flags/flags.json")
DEFAULT_MODEL = "claude-sonnet-5"
_MEDIA = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif"}


def _find_image(name: str) -> Path | None:
    stem = safe_name(name)
    # Prefer PNG (SVGs are converted to PNG by download_images.py).
    for ext in (".png", ".jpg", ".jpeg", ".gif"):
        candidate = IMAGES_DIR / f"{stem}{ext}"
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return None


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        text = text.removeprefix("json")
    return json.loads(text.strip())


def describe_image(client, model: str, image_path: Path) -> dict:
    media_type = _MEDIA.get(image_path.suffix.lower(), "image/png")
    data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")
    message = client.messages.create(
        model=model,
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": data},
                    },
                    {"type": "text", "text": VLM_PROMPT},
                ],
            }
        ],
    )
    return _parse_json(message.content[0].text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--categories", nargs="*", default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set")
    try:
        import anthropic
    except ImportError as exc:
        raise SystemExit("Install anthropic: uv pip install anthropic") from exc

    client = anthropic.Anthropic()
    flags = flaglist_from_json(FLAGS_FILE).flags
    if args.categories:
        flags = [f for f in flags if f.category in set(args.categories)]
    if args.limit:
        flags = flags[: args.limit]

    store = load_descriptions()
    done = skipped = failed = 0
    for i, flag in enumerate(flags, 1):
        if flag.name in store:
            continue
        image = _find_image(flag.name)
        if image is None:
            skipped += 1
            continue
        try:
            store[flag.name] = describe_image(client, args.model, image)
            done += 1
        except Exception as exc:
            failed += 1
            print(f"  fail {flag.name}: {exc}")
        if i % 25 == 0:
            save_descriptions(store)
            print(f"  {i}/{len(flags)} done={done} skip_noimg={skipped} fail={failed}", flush=True)

    save_descriptions(store)
    print(f"Complete: described={done} skipped_no_image={skipped} failed={failed}")


if __name__ == "__main__":
    main()
