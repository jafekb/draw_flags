"""
Utils file for the FlagSearcher & backend.
"""

import json
from pathlib import Path
from typing import List

from pydantic import BaseModel, validator


class Flag(BaseModel):
    """
    Stuff for a single flag - image & metadata
    """

    name: str
    wikipedia_page: str
    wikipedia_url: str
    wikipedia_image_url: str
    local_image_link: str
    verification_method: str = ""
    score: float = 0.0

    @validator("verification_method")
    def validate_my_field(cls, v):
        allowed_values = {"check_options", "commons", "table"}
        if v not in allowed_values:
            raise ValueError(f"Invalid 'verification_method'. Allowed values are: {allowed_values}")
        return v

    def to_json(self, out_dir: Path) -> None:
        if not out_dir.is_dir():
            raise ValueError(f"out_dir must be a valid directory! got '{out_dir}'")
        out_name = out_dir / f"{self.name}.json"

        with out_name.open("w") as f:
            json.dump(self.dict(), f, indent=1)
        return


def flag_from_json(file_name: Path) -> Flag:
    if isinstance(file_name, str):
        print("warning: please use pathlib.Path instead of str :)")
        file_name = Path(file_name)
    if not file_name.is_file():
        raise ValueError(f"File does not exist! {file_name}")

    with file_name.open() as f:
        data = json.load(f)
    return Flag(**data)


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
