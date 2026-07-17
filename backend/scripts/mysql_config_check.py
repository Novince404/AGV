from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from sqlalchemy.engine import make_url


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

os.environ["AGV_DATA_BACKEND"] = "mysql"

from app.core.database import check_database_connection  # noqa: E402
from app.core.settings import get_settings  # noqa: E402
from app.database.maintenance import verify_database  # noqa: E402


def print_line(label: str, value: object) -> None:
    print(f"{label}: {value}")


def mask_database_url(database_url: str) -> str:
    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except Exception:
        return database_url


def main() -> int:
    settings = get_settings()
    ok = True

    print("=== AGV MySQL Config Check ===")
    print_line("backend", settings.data_backend)
    print_line("database_url", mask_database_url(settings.database_url))
    print_line("auto_create", settings.database_auto_create)

    if settings.data_backend != "mysql":
        print("ERROR: AGV_DATA_BACKEND is not mysql")
        return 1

    if not settings.database_url.lower().startswith("mysql+pymysql://"):
        print("ERROR: AGV_DATABASE_URL should start with mysql+pymysql://")
        ok = False

    try:
        importlib.import_module("pymysql")
        print("driver: pymysql available")
    except ModuleNotFoundError:
        print("ERROR: pymysql is not installed in backend venv")
        ok = False

    connected, error_text = check_database_connection()
    if connected:
        print("connection: success")
        verification = verify_database()
        print_line("schema_revision", verification.get("revision"))
        print_line("schema_valid", verification.get("valid"))
        if not verification.get("valid"):
            print("ERROR: MySQL schema is not current; create and verify a backup, then run:")
            print("  python agv.py database upgrade --backup-confirmed")
            ok = False
    else:
        print("ERROR: mysql connection failed")
        print_line("detail", error_text or "unknown error")
        ok = False

    if ok:
        print("MYSQL_CONFIG_OK")
        return 0

    print("MYSQL_CONFIG_FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
