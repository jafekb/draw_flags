"""
Shared helpers for VLM-generated flag descriptions.

Descriptions power the text-to-text retrieval approach: each flag gets a vivid,
country-agnostic visual description (colors, layout, emblems) that a user's query
can match in the *same* modality, instead of the weak cross-modal CLIP path.

Descriptions live inline on each flag as `Flag.visual` (a VisualDescription) in
backend/data/all_flags/flags.json — see backend/scripts/generate_descriptions.py.
"""

from __future__ import annotations

from typing import List

from backend.common.flag_data import VisualDescription

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


def build_document(name: str, visual: VisualDescription | None, *, include_name: bool) -> str:
    """
    Build the text document that gets embedded for a flag.

    With a description, join the sentence + layout + colors + symbols so the
    embedder sees redundant visual vocabulary. Without one, fall back to the name
    so the flag is at least findable by name.
    """
    parts: List[str] = []
    if include_name:
        parts.append(name)
    if visual:
        if visual.description:
            parts.append(visual.description)
        if visual.layout:
            parts.append(visual.layout)
        if visual.colors:
            parts.append(", ".join(visual.colors))
        if visual.symbols:
            parts.append(", ".join(visual.symbols))
    if not parts:
        parts.append(name)
    return ". ".join(parts)
