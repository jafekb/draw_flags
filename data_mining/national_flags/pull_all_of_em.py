#!/usr/bin/python
"""
Let me try something new.
"""

import time
from pathlib import Path

import wikipedia
from tqdm import tqdm

OUT_NAME = Path("/home/bjafek/personal/draw_flags/data_mining/national_flags/flag_pages.txt")
OUT_NAME.touch()
ALREADY_CHECKED_NAME = Path(
    "/home/bjafek/personal/draw_flags/data_mining/national_flags/already_checked_pages.txt"
)
ALREADY_CHECKED_NAME.touch()
IGNORED_NAME = Path("/home/bjafek/personal/draw_flags/data_mining/national_flags/ignored_pages.txt")
IGNORED_NAME.touch()


def get_flag_pages():
    pages = [wikipedia.page("Lists of flags", auto_suggest=False)]
    idx = 0

    with ALREADY_CHECKED_NAME.open("r") as f:
        already_checked = f.read().split("\n")

    with IGNORED_NAME.open("r") as f:
        ignored_pages = f.read().split("\n")

    with OUT_NAME.open("r") as f:
        all_flag_pages = set(f.read().split("\n"))

    while pages:
        idx += 1
        new_pages = []
        n_pages = len(pages)
        for jdx, pp in tqdm(enumerate(pages), total=n_pages, leave=False):
            list_links = []
            flag_links = set()

            for link in tqdm(pp.links, leave=False):
                lower = link.lower()
                if "flags" in lower or "list" in lower:
                    if link in already_checked:
                        continue

                    try:
                        cur_page = wikipedia.page(link, auto_suggest=False)
                    except:  # noqa: E722
                        # If you can't find it just don't worry about it,
                        #  but _don't_ try guessing. I tried to list out the
                        #  exception but there's too many
                        continue
                    list_links.append(cur_page)
                elif "flag of" in lower:
                    flag_links.add(lower)
                else:
                    ignored_pages.append(link)
                already_checked.append(link)

            new_pages.extend(list_links)
            all_flag_pages.update(flag_links)

            # Always write out your flag list whenever you can
            out_list = sorted(all_flag_pages)
            with OUT_NAME.open("w") as f:
                f.write("\n".join(out_list))
            print(f"Wrote out {len(all_flag_pages)} lines to {OUT_NAME}")

            # And keep track of pages we've already listed through
            already_checked = sorted(set(already_checked))
            with ALREADY_CHECKED_NAME.open("w") as f:
                f.write("\n".join(already_checked))
            print(f"Already checked {len(already_checked)} pages.")

            # And keep track of ignored pages
            ignored_pages = sorted(set(ignored_pages))
            with IGNORED_NAME.open("w") as f:
                f.write("\n".join(ignored_pages))
            print(f"Ignored {len(ignored_pages)} pages.")

        pages = new_pages.copy()

        # Tbh not really sure if this will even do enough to stop wikipedia from
        #  getting mad.
        time.sleep(1)


flag_pages = get_flag_pages()
