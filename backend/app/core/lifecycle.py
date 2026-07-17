from __future__ import annotations

from app.core.database import check_database_connection
from app.database.maintenance import database_status, upgrade_database, verify_database
from app.core.settings import get_settings
from app.repositories.runtime import is_sql_backend


def initialize_runtime() -> dict[str, object]:
    settings = get_settings()
    summary: dict[str, object] = {
        "data_backend": settings.data_backend,
        "database_auto_create": settings.database_auto_create,
        "sql_enabled": is_sql_backend(),
    }

    if not is_sql_backend():
        summary["database_status"] = "memory"
        return summary

    connected, error_text = check_database_connection()
    summary["database_status"] = "connected" if connected else "unavailable"
    if error_text:
        summary["database_error"] = error_text

    if not connected:
        return summary

    before = database_status()
    if settings.database_auto_create and before.get("revision") != "0003_auth_password_change_flag":
        # Development/demo convenience only. Production and trial deployments
        # keep this disabled and run the explicit maintenance command.
        migration = upgrade_database()
        summary["migration"] = {
            "from_generation": migration.get("from_generation"),
            "target_revision": migration.get("target_revision"),
            "backup": migration.get("backup"),
        }

    verification = verify_database()
    summary["tables_ready"] = bool(verification.get("valid"))
    summary["schema_revision"] = verification.get("revision")
    if not summary["tables_ready"]:
        summary["schema_error"] = (
            "Database schema is not current. Run `python agv.py database upgrade` "
            "before serving SQL-backed requests."
        )

    return summary
