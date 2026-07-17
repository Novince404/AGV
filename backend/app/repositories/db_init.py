"""Schema readiness checks for SQL repositories.

Schema creation and compatibility changes belong to Alembic migrations.  This
module intentionally performs no DDL; repository calls may only verify that
the application was started against the expected revision.
"""
from __future__ import annotations

import threading

from sqlalchemy.engine import Engine

from app.core.database import get_engine
from app.database.maintenance import HEAD_REVISION, verify_database
from app.repositories.runtime import is_sql_backend


_schema_ready_for_engine: Engine | None = None
_schema_lock = threading.RLock()


def require_current_schema() -> None:
    """Fail early with an actionable error instead of mutating schema in a read.

    The lifecycle runs the same check at startup.  This lightweight guard is
    retained for scripts that call repositories directly.
    """
    global _schema_ready_for_engine
    if not is_sql_backend():
        return
    engine = get_engine()
    if _schema_ready_for_engine is engine:
        return
    with _schema_lock:
        engine = get_engine()
        if _schema_ready_for_engine is engine:
            return
        verification = verify_database()
        if not verification.get("valid"):
            revision = verification.get("revision") or "unversioned"
            raise RuntimeError(
                "Database schema is not ready "
                f"(current={revision}, expected={HEAD_REVISION}). "
                "Run `python agv.py database upgrade` and retry."
            )
        _schema_ready_for_engine = engine


def reset_schema_readiness() -> None:
    global _schema_ready_for_engine
    _schema_ready_for_engine = None
