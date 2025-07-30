"""
Utils file for the FlagSearcher & backend.
"""

import json
from pathlib import Path
from shutil import copyfile
from typing import List

import cairosvg
import requests
from pydantic import BaseModel, validator


class Flag(BaseModel):
    """
    Stuff for a single flag - image & metadata
    """

    name: str
    wikipedia_page: str
    # TODO(bjafek) We could generalize this to just 'info_url' and 'image_url'
    wikipedia_url: str
    wikipedia_image_url: str
    # You don't have to specify this at build time, save_image() can define it for you
    local_image_link: str = ""
    verification_method: str = ""
    score: float = 0.0

    @validator("verification_method")
    def validate_my_field(cls, v):
        allowed_values = {"check_options", "commons", "table"}
        if v not in allowed_values:
            raise ValueError(f"Invalid 'verification_method'. Allowed values are: {allowed_values}")
        return v

    def save_image(self, out_dir: Path) -> None:
        """
        Save the wikipedia_image_url to a local path, and update the local_image_link

        Returns:
            had_to_download(bool) whether or not the file already existed. If it did not,
                then we had to bother wikipedia so we should pause for a sec.
        """
        out_name = out_dir / f"{self.name}.png"
        had_to_download = False
        if not out_name.is_file():
            suffix = self.wikipedia_image_url.split(".")[-1]
            if self.local_image_link:
                # TODO(bjafek) assert suffix in allowed_suffices
                # TODO(bjafek) also feels like we could streamline this logic
                if suffix in ("svg", "SVG"):
                    # TODO(bjafek) just work through this a little more, svgs are tricky
                    # with open(self.local_image_link, "r") as f:
                    # svg = f.read()
                    # out_name = out_dir / f"{self.name}.png"
                    # cairosvg.svg2png(svg, write_to=str(out_name))
                    raise NotImplementedError("I don't want to handle svgs yet!")
                copyfile(self.local_image_link, out_dir / out_name)
                return False

            if suffix in ("svg", "SVG"):
                out_name = out_dir / f"{self.name}.png"
                svg = download_svg(self.wikipedia_image_url)
                cairosvg.svg2png(svg, write_to=str(out_name))
            elif suffix in ("png", "PNG"):
                out_name = out_dir / f"{self.name}.png"
                download_image(self.wikipedia_image_url, out_name)
            elif suffix in ("gif", "GIF"):
                out_name = out_dir / f"{self.name}.gif"
                download_image(self.wikipedia_image_url, out_name)
            elif suffix in ("jpg", "jpeg", "JPG", "JPEG"):
                out_name = out_dir / f"{self.name}.jpg"
                download_image(self.wikipedia_image_url, out_name)
            else:
                raise NotImplementedError(f"We can't yet handle the suffix '{suffix}' you gave us!")
            had_to_download = True
        self.local_image_link = str(out_name)

        return had_to_download

    def to_json(self, out_dir: Path) -> None:
        """
        Save everything to a json in the specified output directory
        """
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


class FlagList(BaseModel):
    """
    Just a bunch of flags
    """

    flags: List[Flag]
    # TODO(bjafek) this should actually be required, I just have to refactor some stuff
    embeddings_filename: str = ""

    # TODO(bjafek) maybe I want to use a standard name, and an out_dir instead?
    def to_json(self, out_name: Path) -> None:
        """
        Save everything to a json in the specified output directory
        """
        if not out_name.parent.is_dir():
            raise ValueError(f"out_name parent must be a valid directory! got '{out_name}'")

        with out_name.open("w") as f:
            json.dump(self.dict(), f, indent=1)
        return


def flaglist_from_json(file_name: Path) -> Flag:
    if isinstance(file_name, str):
        print("warning: please use pathlib.Path instead of str :)")
        file_name = Path(file_name)
    if not file_name.is_file():
        raise ValueError(f"File does not exist! {file_name}")

    with file_name.open() as f:
        data = json.load(f)
    return FlagList(**data)


class Image(BaseModel):
    """
    The data passed between processes for image data
    """

    data: str


def download_image(image_url: str, out_name: Path) -> None:
    """
    Download a jpg/png file from the internet, save it to 'out_name'
    """
    img_data = requests.get(image_url).content
    with out_name.open("wb") as f:
        f.write(img_data)


def download_svg(url: str) -> None:
    """
    Downloads an SVG file from the given URL and saves it with the specified filename.
    https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy

    Args:
    url: The URL of the SVG file.
    filename: The filename to save the downloaded SVG file.
    """
    try:
        response = requests.get(
            url,
            stream=True,
            headers={
                "User-Agent": "DrawFlags/0.0 (https://github.com/jafekb/draw_flags/"
                "; jafek91@gmail.com)"
            },
        )
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error downloading SVG: {e}")
