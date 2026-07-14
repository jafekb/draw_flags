"""Ensure the repo root is importable so `import backend...` works under pytest."""

import sys
from pathlib import Path

ROOT = str(Path(__file__).parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
