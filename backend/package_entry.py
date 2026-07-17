from __future__ import annotations

import asyncio
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

    # A one-folder package has one executable, but it still runs the API and
    # deterministic scheduler in separate processes.  The launcher starts a
    # second copy with ``--scheduler`` after the API has completed migrations.
    # Keeping the roles separate avoids a scheduler restart every time the API
    # process is restarted and matches the Docker trial topology.
    arguments = {argument.strip().lower() for argument in sys.argv[1:]}
    if "database" in arguments:
        from agv import main as database_cli_main

        raise SystemExit(database_cli_main())
    if "--scheduler" in arguments or os.getenv("AGV_RUNTIME_ROLE", "").strip().lower() == "scheduler":
        os.environ["AGV_SCHEDULER_V3_ENABLED"] = "true"
        from scheduler_main import main as scheduler_main

        asyncio.run(scheduler_main())
        return

    # The API must not accidentally own another scheduler when it is launched
    # by start_agv.bat.  The explicit scheduler role above owns the database
    # lease and is the only process that advances simulated vehicles.
    os.environ["AGV_SCHEDULER_V3_ENABLED"] = "false"
    host = os.getenv("AGV_HOST", "127.0.0.1")
    port = int(os.getenv("AGV_PORT", "8000"))

    from main import app

    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
