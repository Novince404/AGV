from __future__ import annotations

from app.core.database import check_database_connection
from app.core.settings import get_settings
from app.repositories.db_init import create_all_tables
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

    if settings.database_auto_create:
        create_all_tables()
        summary["tables_ready"] = True
    else:
        summary["tables_ready"] = False

    return summary
