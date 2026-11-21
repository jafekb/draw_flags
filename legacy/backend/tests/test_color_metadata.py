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


def _coverage(image, names, palette_values, **kw):
    return compute_color_coverage(
        image=image,
        palette_names=names,
        palette_lab_values=palette_values,
        sample_max=image.width * image.height,
        **kw,
    )


def test_color_coverage_simple_flags() -> None:
    """Without edge suppression, clean solid flags quantize to exact proportions."""
    names, palette_values = palette_lab()
    third = float(np.float32(1 / 3))

    poland = Image.open(IMAGES_DIR / "Poland.png")
    assert _coverage(poland, names, palette_values, suppress_edges=False) == {
        "red": 0.5,
        "white": 0.5,
    }

    france = Image.open(IMAGES_DIR / "France.png")
    assert _coverage(france, names, palette_values, suppress_edges=False) == {
        "blue": third,
        "red": third,
        "white": third,
    }

    ireland = Image.open(IMAGES_DIR / "Republic_of_Ireland.png")
    assert _coverage(ireland, names, palette_values, suppress_edges=False) == {
        "green": third,
        "orange": third,
        "white": third,
    }


def test_edge_suppression_preserves_proportions() -> None:
    """With edge suppression on (default), proportions are preserved within tolerance
    while the anti-aliased boundary seams are dropped."""
    names, palette_values = palette_lab()
    france = Image.open(IMAGES_DIR / "France.png")
    cov = _coverage(france, names, palette_values)
    assert set(cov) == {"blue", "red", "white"}
    for color in ("blue", "red", "white"):
        assert abs(cov[color] - 1 / 3) < 0.05
