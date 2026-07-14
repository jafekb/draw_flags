"""
Shared name normalization for the flag eval harness.

Ground truth in queries.json is matched against dataset flag names by normalized
form so that dataset variants ("Bangladesh (variant 2)", "Russia (GOST ...)") match
a clean canonical expected name ("Bangladesh", "Russia").
"""

import re
import unicodedata

_PAREN_RE = re.compile(r"\([^)]*\)")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_name(name: str) -> str:
    """Lowercase, strip diacritics, drop parenthetical qualifiers and punctuation."""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = _PAREN_RE.sub(" ", text)
    text = _NON_ALNUM_RE.sub(" ", text)
    return " ".join(text.split()).strip()
