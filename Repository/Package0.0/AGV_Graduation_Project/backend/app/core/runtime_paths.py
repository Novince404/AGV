from __future__ import annotations

import sys
from pathlib import Path


def is_frozen_runtime() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_backend_root() -> Path:
    if is_frozen_runtime():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def get_project_root() -> Path:
    if is_frozen_runtime():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def get_runtime_root() -> Path:
    return Path(sys.executable).resolve().parent if is_frozen_runtime() else get_project_root()


def get_bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", get_runtime_root())).resolve()


def get_default_frontend_dist_dir() -> Path:
    if is_frozen_runtime():
        return get_bundle_root() / "frontend_dist"
    return get_project_root() / "frontend" / "agv-frontend" / "dist"


def get_default_data_dir() -> Path:
    return get_runtime_root() / "data"


def get_default_sqlite_url(filename: str = "agv_dispatch.db") -> str:
    db_path = (get_default_data_dir() / filename).resolve().as_posix()
    return f"sqlite:///{db_path}"


def get_env_file_candidates() -> list[Path]:
    candidates = [
        get_runtime_root() / ".env",
        get_backend_root() / ".env",
    ]
    unique: list[Path] = []
    for item in candidates:
        resolved = item.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique
