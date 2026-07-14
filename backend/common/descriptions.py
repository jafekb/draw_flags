"""
Shared helpers for VLM-generated flag descriptions.

Descriptions power the text-to-text retrieval approach: each flag gets a vivid,
country-agnostic visual description (colors, layout, emblems) that a user's query
can match in the *same* modality, instead of the weak cross-modal CLIP path.

Descriptions live inline on each flag as `Flag.visual` (a VisualDescription) in
backend/data/all_flags/flags.json — see backend/scripts/generate_descriptions.py.
"""

from __future__ import annotations

from typing import Dict, List

from backend.common.flag_data import Flag

# A palette color counts as "dominant" (worth putting in the search document / a
# dominant-colors chip) at >= 8% coverage; the frontend keeps a lower threshold for
# "contains color X" filtering. light_blue is spelled out for natural queries.
DOMINANT_COLOR_THRESHOLD = 0.08
_COLOR_LABELS = {"light_blue": "light blue"}


def dominant_colors(
    color_coverage: Dict[str, float], threshold: float = DOMINANT_COLOR_THRESHOLD
) -> List[str]:
    items = sorted(
        ((c, v) for c, v in (color_coverage or {}).items() if v >= threshold),
        key=lambda x: -x[1],
    )
    return [_COLOR_LABELS.get(c, c) for c, _ in items]


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


def build_document(flag: Flag, *, include_name: bool) -> str:
    """
    Build the text document that gets embedded for a flag: the VLM description +
    layout + symbols, plus canonical palette color words derived from the quantizer
    (color_coverage) — so free-text color queries match the same vocabulary users can
    filter by. Falls back to the name when a flag has no description.
    """
    parts: List[str] = []
    if include_name:
        parts.append(flag.name)
    if flag.visual:
        if flag.visual.description:
            parts.append(flag.visual.description)
        if flag.visual.layout:
            parts.append(flag.visual.layout)
        if flag.visual.symbols:
            parts.append(", ".join(flag.visual.symbols))
    colors = dominant_colors(flag.color_coverage)
    if colors:
        parts.append(", ".join(colors))
    if not parts:
        parts.append(flag.name)
    return ". ".join(parts)
