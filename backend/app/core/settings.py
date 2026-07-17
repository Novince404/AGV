from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from app.core.runtime_paths import get_default_frontend_dist_dir, get_default_sqlite_url, get_env_file_candidates

ENV_FILE_PATHS = get_env_file_candidates()


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


def _load_env_file() -> dict[str, str]:
    env_values: dict[str, str] = {}
    for env_path in ENV_FILE_PATHS:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            env_values[key.strip()] = value.strip().strip('"').strip("'")
    return env_values


@dataclass(frozen=True)
class AppSettings:
    app_environment: str
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
    auth_session_ttl_sec: int
    auth_session_idle_ttl_sec: int
    auth_cookie_secure: bool
    auth_demo_users_enabled: bool
    bootstrap_admin_username: str | None
    bootstrap_admin_password: str | None
    csrf_enabled: bool
    legacy_api_enabled: bool
    oidc_enabled: bool
    oidc_issuer_url: str | None
    oidc_client_id: str | None
    oidc_client_secret: str | None
    oidc_state_secret: str | None
    frontend_base_url: str
    scheduler_v3_enabled: bool
    scheduler_tick_ms: int
    scheduler_lease_ttl_sec: int
    comfyui_enabled: bool
    comfyui_base_url: str
    comfyui_timeout_sec: int
    serve_frontend_dist: bool
    frontend_dist_dir: str


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    file_env = _load_env_file()

    app_environment = os.getenv(
        "AGV_APP_ENV",
        file_env.get("AGV_APP_ENV", "demo"),
    ).strip().lower()
    if app_environment not in {"demo", "development", "trial", "production", "test"}:
        app_environment = "demo"

    default_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    env_origins = _split_csv(os.getenv("AGV_CORS_ALLOW_ORIGINS", file_env.get("AGV_CORS_ALLOW_ORIGINS")))
    # A production or trial installation must name its browser origins
    # explicitly. Same-origin deployments do not need a CORS allowance.
    origins = env_origins or (default_origins if app_environment in {"demo", "development", "test"} else [])
    default_origin_regex = r"http://(localhost|127\.0\.0\.1):\d+" if app_environment in {"demo", "development", "test"} else ""
    origin_regex = os.getenv(
        "AGV_CORS_ALLOW_ORIGIN_REGEX",
        file_env.get("AGV_CORS_ALLOW_ORIGIN_REGEX", default_origin_regex),
    ) or None

    app_title = os.getenv("AGV_APP_TITLE", file_env.get("AGV_APP_TITLE", "AGV 调度系统后端"))
    root_message = os.getenv("AGV_ROOT_MESSAGE", file_env.get("AGV_ROOT_MESSAGE", "AGV 调度系统后端已启动"))

    data_backend = os.getenv("AGV_DATA_BACKEND", file_env.get("AGV_DATA_BACKEND", "memory")).strip().lower()
    if data_backend not in {"memory", "mysql", "sqlite"}:
        data_backend = "memory"

    database_url = os.getenv(
        "AGV_DATABASE_URL",
        file_env.get(
            "AGV_DATABASE_URL",
            get_default_sqlite_url() if data_backend == "sqlite" else "mysql+pymysql://root:password@127.0.0.1:3306/agv_dispatch?charset=utf8mb4",
        ),
    )
    database_echo = _parse_bool(os.getenv("AGV_DATABASE_ECHO", file_env.get("AGV_DATABASE_ECHO")), False)
    database_auto_create = _parse_bool(
        os.getenv("AGV_DATABASE_AUTO_CREATE", file_env.get("AGV_DATABASE_AUTO_CREATE")),
        app_environment in {"demo", "development", "test"},
    )
    database_connect_timeout_sec = max(
        _parse_int(
            os.getenv("AGV_DATABASE_CONNECT_TIMEOUT_SEC", file_env.get("AGV_DATABASE_CONNECT_TIMEOUT_SEC")),
            5,
        ),
        1,
    )
    database_pool_pre_ping = _parse_bool(
        os.getenv("AGV_DATABASE_POOL_PRE_PING", file_env.get("AGV_DATABASE_POOL_PRE_PING")),
        True,
    )
    auth_session_ttl_sec = max(
        _parse_int(
            os.getenv("AGV_AUTH_SESSION_TTL_SEC", file_env.get("AGV_AUTH_SESSION_TTL_SEC")),
            60 * 60 * 24 * 7,
        ),
        300,
    )
    auth_session_idle_ttl_sec = max(
        _parse_int(
            os.getenv("AGV_AUTH_SESSION_IDLE_TTL_SEC", file_env.get("AGV_AUTH_SESSION_IDLE_TTL_SEC")),
            60 * 60 * 8,
        ),
        300,
    )
    auth_cookie_secure = _parse_bool(
        os.getenv("AGV_AUTH_COOKIE_SECURE", file_env.get("AGV_AUTH_COOKIE_SECURE")),
        app_environment in {"trial", "production"},
    )
    auth_demo_users_enabled = _parse_bool(
        os.getenv("AGV_AUTH_DEMO_USERS_ENABLED", file_env.get("AGV_AUTH_DEMO_USERS_ENABLED")),
        app_environment == "demo",
    )
    bootstrap_admin_username = os.getenv(
        "AGV_BOOTSTRAP_ADMIN_USERNAME",
        file_env.get("AGV_BOOTSTRAP_ADMIN_USERNAME", ""),
    ).strip() or None
    bootstrap_admin_password = os.getenv(
        "AGV_BOOTSTRAP_ADMIN_PASSWORD",
        file_env.get("AGV_BOOTSTRAP_ADMIN_PASSWORD", ""),
    ) or None
    csrf_enabled = _parse_bool(
        os.getenv("AGV_CSRF_ENABLED", file_env.get("AGV_CSRF_ENABLED")),
        app_environment in {"trial", "production"},
    )
    legacy_api_enabled = _parse_bool(
        os.getenv("AGV_LEGACY_API_ENABLED", file_env.get("AGV_LEGACY_API_ENABLED")),
        True,
    )
    oidc_enabled = _parse_bool(
        os.getenv("AGV_OIDC_ENABLED", file_env.get("AGV_OIDC_ENABLED")),
        False,
    )
    oidc_issuer_url = os.getenv("AGV_OIDC_ISSUER_URL", file_env.get("AGV_OIDC_ISSUER_URL", "")).strip().rstrip("/") or None
    oidc_client_id = os.getenv("AGV_OIDC_CLIENT_ID", file_env.get("AGV_OIDC_CLIENT_ID", "")).strip() or None
    oidc_client_secret = os.getenv("AGV_OIDC_CLIENT_SECRET", file_env.get("AGV_OIDC_CLIENT_SECRET", "")) or None
    oidc_state_secret = os.getenv("AGV_OIDC_STATE_SECRET", file_env.get("AGV_OIDC_STATE_SECRET", "")) or None
    frontend_base_url = os.getenv(
        "AGV_FRONTEND_BASE_URL",
        file_env.get("AGV_FRONTEND_BASE_URL", "http://127.0.0.1:5173"),
    ).strip().rstrip("/")
    scheduler_v3_enabled = _parse_bool(
        os.getenv("AGV_SCHEDULER_V3_ENABLED", file_env.get("AGV_SCHEDULER_V3_ENABLED")),
        app_environment == "test",
    )
    scheduler_tick_ms = max(
        _parse_int(os.getenv("AGV_SCHEDULER_TICK_MS", file_env.get("AGV_SCHEDULER_TICK_MS")), 100),
        20,
    )
    scheduler_lease_ttl_sec = max(
        _parse_int(os.getenv("AGV_SCHEDULER_LEASE_TTL_SEC", file_env.get("AGV_SCHEDULER_LEASE_TTL_SEC")), 10),
        3,
    )
    comfyui_enabled = _parse_bool(
        os.getenv("AGV_COMFYUI_ENABLED", file_env.get("AGV_COMFYUI_ENABLED")),
        True,
    )
    comfyui_base_url = os.getenv(
        "AGV_COMFYUI_BASE_URL",
        file_env.get("AGV_COMFYUI_BASE_URL", "http://127.0.0.1:8188"),
    ).strip()
    comfyui_timeout_sec = max(
        _parse_int(
            os.getenv("AGV_COMFYUI_TIMEOUT_SEC", file_env.get("AGV_COMFYUI_TIMEOUT_SEC")),
            20,
        ),
        3,
    )
    serve_frontend_dist = _parse_bool(
        os.getenv("AGV_SERVE_FRONTEND_DIST", file_env.get("AGV_SERVE_FRONTEND_DIST")),
        False,
    )
    frontend_dist_dir = os.getenv(
        "AGV_FRONTEND_DIST_DIR",
        file_env.get("AGV_FRONTEND_DIST_DIR", str(get_default_frontend_dist_dir())),
    )

    return AppSettings(
        app_environment=app_environment,
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
        auth_session_ttl_sec=auth_session_ttl_sec,
        auth_session_idle_ttl_sec=auth_session_idle_ttl_sec,
        auth_cookie_secure=auth_cookie_secure,
        auth_demo_users_enabled=auth_demo_users_enabled,
        bootstrap_admin_username=bootstrap_admin_username,
        bootstrap_admin_password=bootstrap_admin_password,
        csrf_enabled=csrf_enabled,
        legacy_api_enabled=legacy_api_enabled,
        oidc_enabled=oidc_enabled,
        oidc_issuer_url=oidc_issuer_url,
        oidc_client_id=oidc_client_id,
        oidc_client_secret=oidc_client_secret,
        oidc_state_secret=oidc_state_secret,
        frontend_base_url=frontend_base_url,
        scheduler_v3_enabled=scheduler_v3_enabled,
        scheduler_tick_ms=scheduler_tick_ms,
        scheduler_lease_ttl_sec=scheduler_lease_ttl_sec,
        comfyui_enabled=comfyui_enabled,
        comfyui_base_url=comfyui_base_url,
        comfyui_timeout_sec=comfyui_timeout_sec,
        serve_frontend_dist=serve_frontend_dist,
        frontend_dist_dir=frontend_dist_dir,
    )
