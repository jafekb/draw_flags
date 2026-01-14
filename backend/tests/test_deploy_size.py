"""
Lightweight size check to help track deploy footprint.

This is intentionally a print-only test so it can be run locally
and later wired into CI/CD.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple


def _format_bytes(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}PB"


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
    return total


def _largest_files(root: Path, top_n: int = 10, ignore: Iterable[str] = ()) -> Tuple[Tuple[int, Path], ...]:
    ignore_set = set(ignore)
    candidates = []
    for entry in root.rglob("*"):
        if not entry.is_file():
            continue
        parts = set(entry.parts)
        if parts & ignore_set:
            continue
        candidates.append((entry.stat().st_size, entry))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return tuple(candidates[:top_n])


def test_deploy_size() -> None:
    project_root = Path(__file__).resolve().parents[2]

    print("\n📦 Deploy size snapshot")
    print(f"Project root: {project_root}")

    venv_path = project_root / ".venv"
    data_path = project_root / "backend" / "data"
    models_path = project_root / "backend" / "models"

    for label, path in (
        (".venv (deploy deps)", venv_path),
        ("backend/models", models_path),
        ("backend/data", data_path),
    ):
        size = _dir_size(path)
        exists_note = "" if path.exists() else " (missing)"
        print(f"- {label}: {_format_bytes(size)}{exists_note}")

    largest = _largest_files(
        project_root,
        top_n=12,
        ignore={".git", "node_modules", ".venv", "__pycache__"},
    )
    print("\nLargest files (excluding .git, node_modules, .venv):")
    for size, path in largest:
        rel = path.relative_to(project_root)
        print(f"- {_format_bytes(size)}\t{rel}")


if __name__ == "__main__":
    test_deploy_size()
