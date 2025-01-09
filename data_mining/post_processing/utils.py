"""
Process all the files that we downloaded.
"""

import logging
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import wikipedia
from bs4 import BeautifulSoup
from Levenshtein import distance as levenshtein_distance

WIKI_BASE_URL = "https://en.m.wikipedia.org"


def look_at_commons_usage(params, idx, max_length=3):
    """
    If there are too many pages that use the flag, it's probably
    not that helpful.
    """
    # TODO(bjafek) this is actually a lot more useful avenue -
    #  It works for every one, and the page has a 'File Usage' section
    url_base = params["image_url"].split("/")[-1]
    commons_link = f"https://en.m.wikipedia.org/wiki/File:{url_base}"
    params["commons_link"] = commons_link

    try:
        request = Request(commons_link)
        with urlopen(request) as response:
            # read and parse SVG file from URL
            data = response.read()
    except HTTPError:  # 404 not found
        # If it's not a real commons link, just don't bother
        return params
    soup = BeautifulSoup(data, "html.parser")

    # This is how we find the links under "File Usage", which is the most
    #  surefire way of knowing what wikipedia pages are related to this file.
    # See this page for example:
    # https://en.m.wikipedia.org/wiki/File:Flag_of_Offenburg.svg
    file_usage_section = soup.find("div", id="mw-imagepage-section-linkstoimage")
    if file_usage_section is None:
        return params
    links_section = file_usage_section.find("ul")

    all_links = []
    for link_tag in links_section.find_all("a"):
        ref = link_tag["href"]
        if "User" in ref:
            continue
        all_links.append(ref)

    # Many of these flag images show up on a bunch of pages. For example, lists or
    #  galleries of similar flags, or athletes representing that region. If that
    #  is the only page available, I think that's still probably the most
    #  informative page to link the user to, but if we can avoid it we'd prefer
    #  not to. So we'll sort all the links by their similarity to the name of
    #  the flag page, that feels like a good idea and seems to work on a few
    #  simple examples.
    all_links.sort(key=lambda x: levenshtein_distance(url_base, x))

    if not all_links:
        return params

    verified_page = all_links[0]
    flag_page = url_base.split(".")[0]
    verified_url = WIKI_BASE_URL + verified_page
    verified_page = verified_page.replace("/wiki/", "")

    logging.info(f"{idx}: Verified '{flag_page}' on '{verified_page}'")
    params["verified_page"] = verified_page
    params["verified_url"] = verified_url
    params["verification_method"] = "commons"
    return params


def check_options(params, idx):
    """
    This is one way of trying to get the page that the flag corresponds to -
    using the name of the flag to infer what it is about.
    """
    original_flag_page = Path(params["image_path"]).stem
    options = _methods_of_fixing(original_flag_page)
    page = None
    for possible_name in options:
        try:
            # It is very tempting to let auto_suggest=True because we
            #  get a lot more positives, but it introduces too much uncertainty.
            page = wikipedia.page(possible_name, auto_suggest=False)
        except wikipedia.exceptions.PageError:
            continue
        except wikipedia.exceptions.DisambiguationError:
            continue
        break

    if page is None:
        logging.warning(f"{idx}: Skipping '{original_flag_page}', tried {options}")
    else:
        logging.info(
            f"{idx}: Mapping '{original_flag_page}' to '{page.title}' with '{possible_name}'"
        )
        params["verified_page"] = page.title
        params["verified_url"] = page.url
        params["verification_method"] = "check_options"
    return params


def _title_case_preserve_apostrophe(s):
    """
    Converts the string to title case while keeping characters
    after an apostrophe in lowercase.

    Args:
    s: The input string.

    Returns:
    The string in title case with characters after apostrophe lowercase.
    """
    words = s.split()
    titled_words = []
    for word in words:
        if "'" in word:
            parts = word.split("'")
            titled_word = parts[0].title() + "'" + parts[1].lower()
        else:
            titled_word = word.title()
        titled_words.append(titled_word)
    return " ".join(titled_words)


def _sanitize_single_word(word):
    proper_title = _title_case_preserve_apostrophe(word)
    no_the = re.sub(r"^The ", "", proper_title)
    wiki_format = no_the.replace("Of", "of").replace("The", "the")
    return wiki_format


def _sanitize(str_list):
    return [_sanitize_single_word(s) for s in str_list]


def _methods_of_fixing(page_name):
    """
    Give the title a couple of chances to get a similar page.
    During this function, process everything in lowercase,
    then convert to wikipedia standard casing.
    """
    page_name = page_name.lower()

    way1 = page_name
    all_options = [way1]

    if "flag of" not in page_name:
        return all_options

    no_flag = page_name.split("flag of")[1].strip()
    all_options.append(no_flag)

    has_with = re.split("\Wwith\W", no_flag)
    if len(has_with) > 1:
        way3 = has_with[0]
        all_options.append(way3)

    has_of = re.split("\Wof\W", no_flag)
    if len(has_of) > 1:
        way4 = has_of[-1]
        all_options.append(way4)

    # Sometimes the name includes "flag of <name> waving flag>"
    wavings = re.split("\Wwaving\W", no_flag)
    if len(wavings) > 1:
        way5 = wavings[0]
        all_options.append(way5)

    # get rid of anything in parentheses
    paren_reg = r"\(.*?\)"
    has_parens = re.findall(paren_reg, no_flag)
    if has_parens:
        way6 = re.sub(paren_reg, "", no_flag).strip()
        all_options.append(way6)

    # Get rid of all single-character words
    single_char_words = re.sub(r"\b[a-zA-Z]\b", "", no_flag).replace("  ", " ").strip()
    if single_char_words != page_name:
        all_options.append(single_char_words)

    # Sanitize to wikipedia formatting
    sanitized = _sanitize(all_options)
    return sanitized
