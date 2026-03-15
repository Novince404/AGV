from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _split_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(raw: str | None, default: int) -> int:
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class AppSettings:
    app_title: str
    root_message: str
    cors_allow_origins: list[str]
    cors_allow_origin_regex: str | None
    data_backend: str
    database_url: str
    database_echo: bool
    database_auto_create: bool
    database_connect_timeout_sec: int
    database_pool_pre_ping: bool


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    default_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    env_origins = _split_csv(os.getenv("AGV_CORS_ALLOW_ORIGINS"))
    origins = env_origins or default_origins
    origin_regex = os.getenv("AGV_CORS_ALLOW_ORIGIN_REGEX", r"http://(localhost|127\.0\.0\.1):\d+")

    app_title = os.getenv("AGV_APP_TITLE", "AGV 调度系统后端")
    root_message = os.getenv("AGV_ROOT_MESSAGE", "AGV 调度系统后端已启动")

    data_backend = os.getenv("AGV_DATA_BACKEND", "memory").strip().lower()
    if data_backend not in {"memory", "mysql", "sqlite"}:
        data_backend = "memory"

    database_url = os.getenv(
        "AGV_DATABASE_URL",
        "mysql+pymysql://root:password@127.0.0.1:3306/agv_dispatch?charset=utf8mb4",
    )
    database_echo = _parse_bool(os.getenv("AGV_DATABASE_ECHO"), False)
    database_auto_create = _parse_bool(os.getenv("AGV_DATABASE_AUTO_CREATE"), True)
    database_connect_timeout_sec = max(_parse_int(os.getenv("AGV_DATABASE_CONNECT_TIMEOUT_SEC"), 5), 1)
    database_pool_pre_ping = _parse_bool(os.getenv("AGV_DATABASE_POOL_PRE_PING"), True)

    return AppSettings(
        app_title=app_title,
        root_message=root_message,
        cors_allow_origins=origins,
        cors_allow_origin_regex=origin_regex,
        data_backend=data_backend,
        database_url=database_url,
        database_echo=database_echo,
        database_auto_create=database_auto_create,
        database_connect_timeout_sec=database_connect_timeout_sec,
        database_pool_pre_ping=database_pool_pre_ping,
    )
