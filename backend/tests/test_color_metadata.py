"""
Tests for color coverage computation with synthetic flag images.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.scripts.add_color_metadata import compute_color_coverage, palette_lab

IMAGES_DIR = Path(__file__).resolve().parents[1] / "data" / "all_flags" / "images"


def test_color_coverage_simple_flags() -> None:
    names, palette_values = palette_lab()
    third = float(np.float32(1 / 3))

    poland = Image.open(IMAGES_DIR / "Poland.png")
    poland_coverage = compute_color_coverage(
        image=poland,
        palette_names=names,
        palette_lab_values=palette_values,
        sample_max=poland.width * poland.height,
    )
    assert poland_coverage == {"red": 0.5, "white": 0.5}

    france = Image.open(IMAGES_DIR / "France.png")
    france_coverage = compute_color_coverage(
        image=france,
        palette_names=names,
        palette_lab_values=palette_values,
        sample_max=france.width * france.height,
    )
    assert france_coverage == {"blue": third, "red": third, "white": third}

    ireland = Image.open(IMAGES_DIR / "Republic_of_Ireland.png")
    ireland_coverage = compute_color_coverage(
        image=ireland,
        palette_names=names,
        palette_lab_values=palette_values,
        sample_max=ireland.width * ireland.height,
    )
    assert ireland_coverage == {"green": third, "orange": third, "white": third}
