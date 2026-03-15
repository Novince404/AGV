from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings


def _build_engine_kwargs() -> dict[str, object]:
    settings = get_settings()
    kwargs: dict[str, object] = {
        "echo": settings.database_echo,
        "future": True,
    }

    database_url = settings.database_url.lower()
    if settings.data_backend == "sqlite" or database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = settings.database_pool_pre_ping
        kwargs["connect_args"] = {"connect_timeout": settings.database_connect_timeout_sec}

    return kwargs


@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    return create_engine(settings.database_url, **_build_engine_kwargs())


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False, future=True)


def get_db_session() -> Session:
    factory = get_session_factory()
    return factory()


def check_database_connection() -> tuple[bool, str | None]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:  # pragma: no cover - startup diagnostic path
        return False, str(exc)


def dispose_engine() -> None:
    try:
        get_engine().dispose()
    except Exception:
        return
