"""
Utils file for the FlagSearcher & backend.
"""
from pydantic import BaseModel
from typing import List


class Flag(BaseModel):
    """
    Stuff for a single flag - image & metadata
    """
    name: str
    wikipedia_link: str = "wiki"
    image_link: str = ""
    score: float = 0.


class Flags(BaseModel):
    """
    Just a bunch of flags
    """
    flags: List[Flag]

class Image(BaseModel):
    """
    """
    data: str


def get_wikipedia_link(name):
    # TODO(bjafek) shouldn't just be the USA flag every time
    return "https://en.wikipedia.org/wiki/Flag_of_the_United_States"


def get_image_link(name):
    # TODO(bjafek) shouldn't just be the USA flag every time
    return "/home/bjafek/personal/draw_flags/flag_ims/usa/usa.png"
