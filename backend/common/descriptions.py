"""
Shared helpers for VLM-generated flag descriptions.

Descriptions power the text-to-text retrieval approach: each flag gets a vivid,
country-agnostic visual description (colors, layout, emblems) that a user's query
can match in the *same* modality, instead of the weak cross-modal CLIP path.

Store format (backend/data/all_flags/descriptions.json):
    { "<flag name>": {
        "description": str,   # one vivid sentence, no country name
        "layout": str,        # e.g. "horizontal triband", "canton", "saltire", "plain"
        "colors": [str],      # dominant colors
        "symbols": [str]      # charges/emblems, e.g. "crescent", "five-pointed star"
    }, ... }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

DESCRIPTIONS_FILE = Path("backend/data/all_flags/descriptions.json")

# Prompt shared by the API script and the in-harness generation so descriptions
# stay consistent. Deliberately forbids naming the country: we want visual words
# a searcher would type, and we must not rely on name knowledge for obscure flags.
VLM_PROMPT = (
    "You are describing a flag image for a visual search engine. Describe ONLY what "
    "is visually present. Do NOT name the country, region, or organization, and do "
    "not guess whose flag it is.\n\n"
    "Return a single JSON object with keys:\n"
    '  "description": one vivid sentence a person might type to find this flag, '
    "covering the colors, their arrangement/layout, and any emblems or charges;\n"
    '  "layout": short phrase, e.g. "horizontal triband", "vertical triband", '
    '"bicolor", "canton", "saltire", "cross", "diagonal", "plain field", "complex";\n'
    '  "colors": array of dominant colors (lowercase, e.g. "red", "white", "green", '
    '"light blue", "yellow", "black");\n'
    '  "symbols": array of emblems/charges visible, e.g. "crescent", '
    '"five-pointed star", "sun with face", "eagle", "cross", "maple leaf", '
    '"coat of arms", "star and crescent"; empty array if none.\n\n'
    "Output only the JSON object, nothing else."
)


def load_descriptions() -> Dict[str, dict]:
    if not DESCRIPTIONS_FILE.exists():
        return {}
    with DESCRIPTIONS_FILE.open() as f:
        return json.load(f)


def save_descriptions(store: Dict[str, dict]) -> None:
    DESCRIPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DESCRIPTIONS_FILE.open("w") as f:
        json.dump(store, f, indent=1, ensure_ascii=False, sort_keys=True)


def build_document(flag_name: str, entry: dict | None, *, include_name: bool) -> str:
    """
    Build the text document that gets embedded for a flag.

    With a description, join the sentence + layout + colors + symbols so the
    embedder sees redundant visual vocabulary. Without one, fall back to the name
    so the flag is at least findable by name.
    """
    parts: List[str] = []
    if include_name:
        parts.append(flag_name)
    if entry:
        if entry.get("description"):
            parts.append(entry["description"])
        if entry.get("layout"):
            parts.append(entry["layout"])
        if entry.get("colors"):
            parts.append(", ".join(entry["colors"]))
        if entry.get("symbols"):
            parts.append(", ".join(entry["symbols"]))
    if not parts:
        parts.append(flag_name)
    return ". ".join(parts)
