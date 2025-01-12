"""
Utils file for the FlagSearcher & backend.
"""

from typing import List

from pydantic import BaseModel


class Flag(BaseModel):
    """
    Stuff for a single flag - image & metadata
    """

    name: str
    wikipedia_page: str
    wikipedia_link: str
    wikipedia_image_link: str
    local_image_link: str
    verification_method: str
    score: float = 0.0


class Flags(BaseModel):
    """
    Just a bunch of flags
    """

    flags: List[Flag]


class Image(BaseModel):
    """
    The data passed between processes for image data
    """

    data: str


def get_wikipedia_link(name):
    # TODO(bjafek) shouldn't just be the USA flag every time
    return "https://en.wikipedia.org/wiki/Flag_of_the_United_States"


def get_image_link(name):
    # TODO(bjafek) shouldn't just be the USA flag every time
    return "/home/bjafek/personal/draw_flags/flag_ims/usa/usa.png"
