from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


def _runtime_root() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def _bundle_root(runtime_root: Path) -> Path:
    return Path(getattr(sys, "_MEIPASS", runtime_root)).resolve()


def _env_file_exists(runtime_root: Path) -> bool:
    return (runtime_root / ".env").exists()


def _resolve_shared_sqlite_path(runtime_root: Path) -> Path:
    data_dir = runtime_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    candidates = [
        runtime_root.parent.parent / "data" / "agv_dispatch.db",
        runtime_root.parent / "AGV_Dispatch_Package_v2" / "data" / "agv_dispatch.db",
        runtime_root.parent / "AGV_Dispatch_Package" / "data" / "agv_dispatch.db",
        data_dir / "agv_dispatch.db",
        data_dir / "agv_enterprise_client.db",
    ]
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists():
            return resolved
    return (data_dir / "agv_dispatch.db").resolve()


def _configure_packaged_environment() -> None:
    runtime_root = _runtime_root()
    bundle_root = _bundle_root(runtime_root)
    frontend_dist_dir = (bundle_root / "frontend_dist").resolve()

    os.environ.setdefault("AGV_SERVE_FRONTEND_DIST", "true")
    os.environ.setdefault("AGV_FRONTEND_DIST_DIR", str(frontend_dist_dir))
    os.environ.setdefault("AGV_APP_TITLE", "AGV 企业独立客户端后端")
    os.environ.setdefault("AGV_ROOT_MESSAGE", "AGV 企业独立客户端后端已启动")

    external_backend = os.getenv("AGV_DATA_BACKEND")
    external_database = os.getenv("AGV_DATABASE_URL")
    if external_backend or external_database or _env_file_exists(runtime_root):
        os.environ.setdefault("AGV_DATABASE_AUTO_CREATE", "true")
        return

    sqlite_path = _resolve_shared_sqlite_path(runtime_root).as_posix()
    os.environ.setdefault("AGV_DATA_BACKEND", "sqlite")
    os.environ.setdefault("AGV_DATABASE_URL", f"sqlite:///{sqlite_path}")
    os.environ.setdefault("AGV_DATABASE_AUTO_CREATE", "true")


def main() -> None:
    _configure_packaged_environment()
    host = os.getenv("AGV_HOST", "127.0.0.1")
    port = int(os.getenv("AGV_PORT", "8010"))

    from main import app

    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
