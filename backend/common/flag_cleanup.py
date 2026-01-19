"""
Helpers for cleaning flag metadata during dataset generation.
"""

from __future__ import annotations

import re
import time
from typing import Iterable, List, Sequence, Set, Tuple

import requests

from backend.common.flag_data import Flag

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "DrawFlags/0.0 (https://github.com/jafekb/draw_flags; jafek91@gmail.com)"


def _title_case_name(name: str) -> str:
    lower_words = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "but",
        "by",
        "for",
        "from",
        "in",
        "into",
        "nor",
        "of",
        "on",
        "onto",
        "or",
        "over",
        "per",
        "the",
        "to",
        "up",
        "via",
        "vs",
        "vs.",
        "with",
        "de",
        "la",
        "del",
        "della",
        "di",
        "du",
        "le",
        "el",
        "al",
        "von",
        "van",
        "der",
        "das",
    }

    def titlecase_token(token: str, *, is_first: bool) -> str:
        match = re.match(r"^(\W*)(.+?)(\W*)$", token)
        if not match:
            return token
        lead, body, trail = match.groups()
        if not re.search(r"[A-Za-z]", body):
            return token

        def titlecase_word(word: str, *, is_first: bool) -> str:
            if not word:
                return word
            if word.isupper():
                return word
            if any(c.isupper() for c in word[1:]):
                return word
            lower = word.lower()
            if lower in lower_words and not is_first:
                return lower
            return lower[:1].upper() + lower[1:]

        parts = re.split(r"(-)", body)
        result = []
        first_word = True
        for part in parts:
            if part == "-":
                result.append(part)
                continue
            if not re.search(r"[A-Za-z]", part):
                result.append(part)
                continue
            result.append(titlecase_word(part, is_first=is_first if first_word else False))
            first_word = False
        return lead + "".join(result) + trail

    tokens = name.split(" ")
    out: List[str] = []
    first_word = True
    for token in tokens:
        if token == "":
            out.append(token)
            continue
        out.append(titlecase_token(token, is_first=first_word))
        if re.search(r"[A-Za-z]", token):
            first_word = False
    return " ".join(out)


def _normalize_date_name(flag: Flag) -> None:
    name = flag.name
    date_only = re.compile(r"^[0-9\u2013, ()]+$")

    if date_only.match(name) and flag.wikipedia_page.startswith("Flag_of_"):
        entity = flag.wikipedia_page[len("Flag_of_") :].replace("_", " ").strip()
        if entity:
            name = f"Flag of {entity} ({name})"

    if name.startswith("Flag of ") and re.search(r"\([0-9]", name):
        name = name[len("Flag of ") :]

    if name and name[0].islower():
        name = _title_case_name(name)

    flag.name = name


def _apply_prefix(flag: Flag, prefix: str) -> None:
    if flag.name.startswith(f"{prefix} - "):
        return
    flag.name = f"{prefix} - {flag.name}"


def _map_flag_to_page(flag: Flag, page: str, title: str, *, prefix: bool = True) -> None:
    flag.wikipedia_page = page
    flag.wikipedia_url = f"https://en.wikipedia.org/wiki/{page}"
    if prefix:
        _apply_prefix(flag, title)


def _missing_page_batches(pages: Sequence[str], batch_size: int = 50) -> Iterable[List[str]]:
    for idx in range(0, len(pages), batch_size):
        yield list(pages[idx : idx + batch_size])


def find_missing_wikipedia_pages(pages: Iterable[str], sleep_seconds: float = 0.1) -> Set[str]:
    pages = [page for page in pages if page]
    if not pages:
        return set()

    missing: Set[str] = set()
    headers = {"User-Agent": USER_AGENT}

    for batch in _missing_page_batches(pages):
        params = {
            "action": "query",
            "format": "json",
            "titles": "|".join(batch),
            "redirects": 1,
        }
        try:
            response = requests.get(WIKIPEDIA_API, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            # If the API fails, return no missing pages so we only do name cleanup.
            return set()

        pages_dict = payload.get("query", {}).get("pages", {})
        for page_id, info in pages_dict.items():
            if str(page_id) == "-1" or info.get("missing") is not None:
                title = info.get("title")
                if title:
                    missing.add(title)

        time.sleep(sleep_seconds)

    return missing


def _match_rule(flag: Flag) -> Tuple[str, str, bool] | None:
    name = flag.name
    page = flag.wikipedia_page
    image_url = flag.wikipedia_image_url

    rules: List[Tuple[re.Pattern, Tuple[str, str, bool]]] = [
        (
            re.compile(r"Design by |Proposal .*PRC flag|Zeng Liansong", re.IGNORECASE),
            ("List_of_Chinese_flags", "List of Chinese flags", True),
        ),
        (
            re.compile(
                r"Proposal for the Flag of South Africa|1910 proposal|Committee proposal|"
                r"Proposal by ANC|Naval ensign|Naval colour|South African Defence Force|"
                r"Air Force Ensign",
                re.IGNORECASE,
            ),
            ("List_of_South_African_flags", "List of South African flags", True),
        ),
        (
            re.compile(
                r"Yacht Club|Club N\u00e1utico|Club Nautico|Club Regatas|"
                r"Club de Veleros|Club Mendoza de Regatas|Club San Fernando|"
                r"Club Universitario|Club Suizo|Caption=Club",
                re.IGNORECASE,
            ),
            ("List_of_yacht_clubs", "List of yacht clubs", True),
        ),
        (
            re.compile(r"War flag \(official\)", re.IGNORECASE),
            ("Darul_Islam_(Indonesia)", "Darul Islam (Indonesia)", True),
        ),
        (
            re.compile(r"Flag of Riga", re.IGNORECASE),
            ("Riga", "Riga", True),
        ),
        (
            re.compile(r"Sultan of Palembang|Palace Guard Flag", re.IGNORECASE),
            ("Palembang_Sultanate", "Palembang Sultanate", True),
        ),
        (
            re.compile(r"Po\u017earevca", re.IGNORECASE),
            ("Po\u017earevac", "Po\u017earevac", True),
        ),
        (
            re.compile(r"Zemun \(", re.IGNORECASE),
            ("Zemun", "Zemun", True),
        ),
        (
            re.compile(r"Flag of the Organized Village of Kake", re.IGNORECASE),
            ("Kake,_Alaska", "Kake, Alaska", True),
        ),
        (
            re.compile(r"Flag of Sumatra under Dutch rule", re.IGNORECASE),
            ("Sumatra", "Sumatra", True),
        ),
        (
            re.compile(r"Royal Flag of The Netherlands", re.IGNORECASE),
            ("Netherlands", "Netherlands", True),
        ),
        (
            re.compile(r"Distinctive flag of a resident of the Dutch East Indies", re.IGNORECASE),
            ("Dutch_East_Indies", "Dutch East Indies", True),
        ),
        (
            re.compile(
                r"Depiction of the coats of arms|Coat of arms of Glarus",
                re.IGNORECASE,
            ),
            ("Coat_of_arms_of_Switzerland", "Coat of arms of Switzerland", True),
        ),
        (
            re.compile(r"Depiction of the flag with Schwenkel", re.IGNORECASE),
            ("Flag_of_Switzerland", "Flag of Switzerland", True),
        ),
        (
            re.compile(r"Checheno-Ingushetia", re.IGNORECASE),
            (
                "Checheno-Ingush_Autonomous_Soviet_Socialist_Republic",
                "Checheno-Ingush ASSR",
                True,
            ),
        ),
        (
            re.compile(r"Another variant of the practice flag", re.IGNORECASE),
            ("Indonesia", "Indonesia", True),
        ),
        (
            re.compile(r"Air Tiris|Landak|Mekongga|Bicoli", re.IGNORECASE),
            ("Indonesia", "Indonesia", True),
        ),
        (
            re.compile(
                r"Flag of the Ministry of Defence|Flag of the Ministry of State Apparatus|"
                r"Flag of the Deputy Minister of East Indonesia",
                re.IGNORECASE,
            ),
            ("Indonesia", "Indonesia", True),
        ),
        (
            re.compile(r"Naval ensign of New York", re.IGNORECASE),
            ("New_York", "New York", True),
        ),
    ]

    for pattern, target in rules:
        if pattern.search(name) or pattern.search(page) or pattern.search(image_url):
            return target
    return None


def clean_flags(flags: List[Flag], *, validate_wikipedia: bool = True) -> List[Flag]:
    for flag in flags:
        _normalize_date_name(flag)

    missing_pages: Set[str] = set()
    if validate_wikipedia:
        missing_pages = find_missing_wikipedia_pages({flag.wikipedia_page for flag in flags})

    for flag in flags:
        if flag.wikipedia_page in missing_pages:
            target = _match_rule(flag)
            if target:
                page, title, prefix = target
                _map_flag_to_page(flag, page, title, prefix=prefix)
                if flag.name and flag.name[0].islower():
                    flag.name = _title_case_name(flag.name)

    return flags
