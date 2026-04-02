from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


def _configure_packaged_environment() -> None:
    runtime_root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    bundle_root = Path(getattr(sys, "_MEIPASS", runtime_root)).resolve()
    data_dir = runtime_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    sqlite_path = (data_dir / "agv_enterprise_client.db").resolve().as_posix()
    frontend_dist_dir = (bundle_root / "frontend_dist").resolve()

    os.environ.setdefault("AGV_DATA_BACKEND", "sqlite")
    os.environ.setdefault("AGV_DATABASE_URL", f"sqlite:///{sqlite_path}")
    os.environ.setdefault("AGV_DATABASE_AUTO_CREATE", "true")
    os.environ.setdefault("AGV_SERVE_FRONTEND_DIST", "true")
    os.environ.setdefault("AGV_FRONTEND_DIST_DIR", str(frontend_dist_dir))
    os.environ.setdefault("AGV_APP_TITLE", "AGV 企业独立客户端后端")
    os.environ.setdefault("AGV_ROOT_MESSAGE", "AGV 企业独立客户端后端已启动")


def main() -> None:
    _configure_packaged_environment()
    host = os.getenv("AGV_HOST", "127.0.0.1")
    port = int(os.getenv("AGV_PORT", "8010"))

    from main import app

    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
