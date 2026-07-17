from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.runtime_paths import get_bundle_root, is_frozen_runtime


@lru_cache(maxsize=1)
def get_version() -> str:
    """Read the single repository version source without depending on cwd."""

    # PyInstaller places data files in its bundle directory while the normal
    # repository layout keeps VERSION three levels above this module.
    version_file = (
        get_bundle_root() / "VERSION"
        if is_frozen_runtime()
        else Path(__file__).resolve().parents[3] / "VERSION"
    )
    try:
        value = version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0+unknown"
    return value or "0.0.0+unknown"
