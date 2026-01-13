"""
Utils file for the FlagSearcher & backend.
"""

import json
from pathlib import Path
from shutil import copyfile
from typing import List, Optional

import requests
from pydantic import BaseModel, field_validator

# Only import cairosvg when needed for data preparation
try:
    import cairosvg

    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False


class Flag(BaseModel):
    """
    Flag data model with metadata for searchability and organization.
    """

    # Core identification
    name: str
    wikipedia_page: str
    wikipedia_url: str
    wikipedia_image_url: str

    # New metadata fields for enhanced searchability
    category: str  # "national", "subdivision", "city", "organization", "historical", "fotw"
    entity_type: str  # "country", "state", "province", "territory", "city", "organization", "historical"
    country: Optional[str] = None  # Parent country for subdivisions/cities
    adoption_year: Optional[int] = None  # Year flag was adopted
    tags: List[str] = []  # Searchable keywords
    
    # Query result field (not stored in database, used only for search results)
    score: Optional[float] = None  # Similarity score from search queries

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        allowed_values = {"national", "subdivision", "city", "organization", "historical", "fotw"}
        if v not in allowed_values:
            raise ValueError(f"Invalid 'category'. Allowed values are: {allowed_values}")
        return v

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v):
        allowed_values = {"country", "state", "province", "territory", "city", "organization", "historical"}
        if v not in allowed_values:
            raise ValueError(f"Invalid 'entity_type'. Allowed values are: {allowed_values}")
        return v

    def save_image(self, out_dir: Path) -> bool:
        """
        Save the wikipedia_image_url to a local path.

        Returns:
            had_to_download(bool) whether or not the file already existed. If it did not,
                then we had to bother wikipedia so we should pause for a sec.
        """
        if not CAIROSVG_AVAILABLE:
            raise ImportError(
                "cairosvg is required for save_image() but not available in production"
            )

        suffix = self.wikipedia_image_url.split(".")[-1]
        
        if suffix in ("svg", "SVG"):
            out_name = out_dir / f"{self.name}.png"
        elif suffix in ("png", "PNG"):
            out_name = out_dir / f"{self.name}.png"
        elif suffix in ("gif", "GIF"):
            out_name = out_dir / f"{self.name}.gif"
        elif suffix in ("jpg", "jpeg", "JPG", "JPEG"):
            out_name = out_dir / f"{self.name}.jpg"
        else:
            raise NotImplementedError(f"We can't yet handle the suffix '{suffix}' you gave us!")

        if out_name.is_file():
            return False

        if suffix in ("svg", "SVG"):
            svg = download_svg(self.wikipedia_image_url)
            cairosvg.svg2png(svg, write_to=str(out_name))
        else:
            download_image(self.wikipedia_image_url, out_name)

        return True

    def to_json(self, out_dir: Path) -> None:
        """
        Save everything to a json in the specified output directory
        """
        if not out_dir.is_dir():
            raise ValueError(f"out_dir must be a valid directory! got '{out_dir}'")
        out_name = out_dir / f"{self.name}.json"

        with out_name.open("w") as f:
            json.dump(self.model_dump(), f, indent=1)
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
            json.dump(self.model_dump(), f, indent=1)
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
