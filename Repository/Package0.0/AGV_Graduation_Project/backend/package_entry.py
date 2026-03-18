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

    sqlite_path = (data_dir / "agv_dispatch.db").resolve().as_posix()
    frontend_dist_dir = (bundle_root / "frontend_dist").resolve()

    os.environ.setdefault("AGV_DATA_BACKEND", "sqlite")
    os.environ.setdefault("AGV_DATABASE_URL", f"sqlite:///{sqlite_path}")
    os.environ.setdefault("AGV_DATABASE_AUTO_CREATE", "true")
    os.environ.setdefault("AGV_SERVE_FRONTEND_DIST", "true")
    os.environ.setdefault("AGV_FRONTEND_DIST_DIR", str(frontend_dist_dir))


def main() -> None:
    _configure_packaged_environment()

    from main import app

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
