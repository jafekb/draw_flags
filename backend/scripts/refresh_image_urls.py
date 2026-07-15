#!/usr/bin/env python3
"""
Repair stale flag image URLs. Some scraped wikipedia_image_url values now 404 on
Wikimedia (the file was renamed/replaced), which renders as a blank flag in the UI.

For each candidate flag we check whether its current URL still resolves; if not, we
re-resolve its flag image in order of fidelity: (0) follow the stored file's rename
redirect (recovers the literal same file at its new name); (1) the article lead
image if it looks like a flag; (2) the best flag-named file used on the page. Every
candidate must look like a flag AND share a place-token with the entity, so we never
adopt a non-flag photo or another entity's flag — a blank beats a wrong flag.
Candidates default to flags with no local downloaded image; --all checks every flag.

Usage:
    uv run backend/scripts/refresh_image_urls.py            # fix the known-missing set
    uv run backend/scripts/refresh_image_urls.py --all      # check every flag (slow)
"""

from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
import urllib.parse
from pathlib import Path

import requests

from backend.scripts.download_images import IMAGES_DIR, safe_name

FLAGS_FILE = Path("backend/data/all_flags/flags.json")
API = "https://en.wikipedia.org/w/api.php"
UA = "DrawFlags/0.1 (https://github.com/jafekb/draw_flags; jafek91@gmail.com)"
HEADERS = {"User-Agent": UA}


def url_ok(url: str) -> bool:
    """True iff the URL resolves (200). Retries on 429 so rate-limiting is not
    mistaken for a broken URL; only a real 4xx/5xx (or exhausted retries) is False."""
    backoff = 3.0
    for _ in range(5):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        except requests.exceptions.RequestException:
            return False
        if r.status_code == 429:
            time.sleep(float(r.headers.get("retry-after", backoff)))
            backoff = min(backoff * 2, 30)
            continue
        return r.status_code == 200
    return False  # kept getting 429; treat as unresolved this run


# Only adopt an image whose filename looks like a flag — never an article's lead
# *photo* (e.g. a cityscape for a city article), which would be worse than a blank.
FLAG_KW = (
    "flag",
    "bandera",
    "vlag",
    "drapeau",
    "bendera",
    "zastava",
    "wappen",
    "vexil",
    "flagge",
    "banner",
    "veliav",
    "vėliav",
    "flago",
    "lippu",
    "bandeira",
    "bandiera",
    "vlajka",
    "zászló",
    "прапор",
    "флаг",
)


_GENERIC = {
    "flag",
    "flags",
    "the",
    "of",
    "and",
    "historical",
    "variant",
    "city",
    "province",
    "state",
    "island",
    "games",
    "republic",
    "socialist",
    "soviet",
    "kingdom",
    "region",
    "federal",
    "people",
    "peoples",
    "democratic",
    "union",
    "council",
    "federation",
    "autonomous",
    "district",
    "county",
    "old",
    "new",
    "symbols",
}


def _norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s.lower()


def _looks_like_flag(filename: str) -> bool:
    return any(k in _norm(filename) for k in FLAG_KW)


def _place_tokens(name: str, page: str) -> set:
    toks = re.split(r"[^a-z0-9]+", _norm(f"{name} {page.replace('_', ' ')}"))
    return {t for t in toks if len(t) > 3 and t not in _GENERIC}


def _belongs(filename: str, place_tokens: set) -> bool:
    """A candidate flag file belongs to this entity only if its name shares a
    place-token — otherwise it's some other entity's flag that merely appears on the
    same article (e.g. Flag_of_Brazil on the Abidjan page)."""
    fn = _norm(filename)
    return any(tok in fn for tok in place_tokens)


def _api(params: dict) -> dict:
    try:
        r = requests.get(API, params={**params, "format": "json"}, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()
    except (requests.exceptions.RequestException, ValueError):
        return {}


def _lead_image(title: str) -> str | None:
    pages = (
        _api(
            {
                "action": "query",
                "titles": title,
                "prop": "pageimages",
                "piprop": "original",
                "redirects": "1",
            }
        )
        .get("query", {})
        .get("pages", {})
    )
    for page in pages.values():
        src = page.get("original", {}).get("source")
        if src:
            return src
    return None


def _file_url(file_title: str) -> str | None:
    pages = (
        _api({"action": "query", "titles": file_title, "prop": "imageinfo", "iiprop": "url"})
        .get("query", {})
        .get("pages", {})
    )
    for page in pages.values():
        info = page.get("imageinfo")
        if info:
            return info[0].get("url")
    return None


def _canonical_url(stored_url: str) -> str | None:
    """Follow the stored file's rename: query imageinfo on its filename with
    redirects, returning the current canonical URL (Wikimedia keeps a file redirect
    when a file is renamed, so this recovers the new location directly)."""
    filename = urllib.parse.unquote(stored_url.rstrip("/").rsplit("/", 1)[-1])
    pages = (
        _api(
            {
                "action": "query",
                "titles": f"File:{filename}",
                "prop": "imageinfo",
                "iiprop": "url",
                "redirects": "1",
            }
        )
        .get("query", {})
        .get("pages", {})
    )
    for page in pages.values():
        info = page.get("imageinfo")
        if info:
            return info[0].get("url")
    return None


def resolve_flag_image(name: str, wikipedia_page: str, stored_url: str) -> str | None:
    """Find THIS entity's flag. First follow the stored file's rename redirect; then
    fall back to the article's lead image (if a flag) or the best flag-named file on
    the page. Only ever adopts a flag that belongs to the entity, never another's."""
    title = wikipedia_page.replace("_", " ")
    place_tokens = _place_tokens(name, wikipedia_page)

    # tier 0: the same file, renamed (most faithful — it's literally the old file)
    canon = _canonical_url(stored_url)
    if canon:
        cf = urllib.parse.unquote(canon.rsplit("/", 1)[-1])
        if _looks_like_flag(cf) and _belongs(cf, place_tokens):
            return canon

    lead = _lead_image(title)
    if lead:
        fn = lead.rsplit("/", 1)[-1]
        if _looks_like_flag(fn) and _belongs(fn, place_tokens):
            return lead

    images = (
        _api(
            {
                "action": "query",
                "titles": title,
                "prop": "images",
                "imlimit": "500",
                "redirects": "1",
            }
        )
        .get("query", {})
        .get("pages", {})
    )
    titles = [im["title"] for p in images.values() for im in p.get("images", [])]
    flag_titles = [t for t in titles if _looks_like_flag(t) and _belongs(t, place_tokens)]
    flag_titles.sort(key=lambda t: t.lower().endswith(".svg"), reverse=True)
    for t in flag_titles:
        url = _file_url(t)
        if url and url_ok(url):
            return url
    return None


def has_local_image(name: str) -> bool:
    stem = safe_name(name)
    return any(
        (IMAGES_DIR / f"{stem}{e}").exists() and (IMAGES_DIR / f"{stem}{e}").stat().st_size > 0
        for e in (".png", ".jpg", ".jpeg", ".gif")
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="check every flag, not just missing ones")
    ap.add_argument("--delay", type=float, default=0.5)
    args = ap.parse_args()

    data = json.loads(FLAGS_FILE.read_text())
    flags = data["flags"]
    candidates = flags if args.all else [f for f in flags if not has_local_image(f["name"])]
    print(f"Checking {len(candidates)} candidate flags...")

    fixed = still_broken = ok = 0
    for f in candidates:
        if url_ok(f["wikipedia_image_url"]):
            ok += 1
            continue
        new = resolve_flag_image(f["name"], f["wikipedia_page"], f["wikipedia_image_url"])
        time.sleep(args.delay)
        if new and new != f["wikipedia_image_url"] and url_ok(new):
            print(f"  FIXED  {f['name']}\n         {f['wikipedia_image_url']}\n      -> {new}")
            f["wikipedia_image_url"] = new
            fixed += 1
        else:
            print(f"  STILL BROKEN  {f['name']}  ({f['wikipedia_image_url']})")
            still_broken += 1
        time.sleep(args.delay)

    FLAGS_FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(f"\nDone. ok={ok} fixed={fixed} still_broken={still_broken}")


if __name__ == "__main__":
    main()
