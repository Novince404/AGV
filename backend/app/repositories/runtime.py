from __future__ import annotations

from app.core.settings import get_settings


def get_data_backend() -> str:
    return get_settings().data_backend


def is_memory_backend() -> bool:
    return get_data_backend() == "memory"


def is_sql_backend() -> bool:
    return get_data_backend() in {"mysql", "sqlite"}

