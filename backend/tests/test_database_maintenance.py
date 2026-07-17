from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.core.database import dispose_engine
from app.core.settings import get_settings
from app.database.maintenance import (
    HEAD_REVISION,
    backup_database,
    restore_database,
    upgrade_database,
    verify_database,
)
from app.repositories.db_init import reset_schema_readiness


@pytest.fixture
def sqlite_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Configure an isolated, file-backed database for migration tests."""
    dispose_engine()
    get_settings.cache_clear()
    db_path = tmp_path / "agv-maintenance.db"
    monkeypatch.setenv("AGV_APP_ENV", "development")
    monkeypatch.setenv("AGV_DATA_BACKEND", "sqlite")
    monkeypatch.setenv("AGV_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("AGV_DATABASE_AUTO_CREATE", "false")
    get_settings.cache_clear()
    reset_schema_readiness()
    try:
        yield db_path
    finally:
        dispose_engine()
        get_settings.cache_clear()
        reset_schema_readiness()


def _drop_v3_foundation(connection: sqlite3.Connection) -> None:
    for table_name in (
        "idempotency_record",
        "scheduler_lease",
        "runtime_command",
        "runtime_event",
        "oidc_link_request",
        "oidc_identity",
        "alembic_version",
    ):
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")


def _drop_column(connection: sqlite3.Connection, table_name: str, column_name: str) -> None:
    # SQLite requires dependent indexes to be removed before a column can be
    # dropped. The migration should recreate only columns, not hidden runtime
    # compatibility DDL, so these deliberately emulate older stored schemas.
    indexes = connection.execute(f"PRAGMA index_list({table_name})").fetchall()
    for index in indexes:
        index_name = str(index[1])
        index_columns = connection.execute(f"PRAGMA index_info({index_name})").fetchall()
        if any(str(item[2]) == column_name for item in index_columns):
            connection.execute(f"DROP INDEX IF EXISTS {index_name}")
    connection.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")


def _seed_database(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO auth_user (
            id, username, display_name, role, password_hash, must_change_password,
            active, builtin, account_status
        ) VALUES ('migration-user', 'migration-user', 'Before upgrade', 'personal', 'hash', 0, 1, 0, 'approved')
        """
    )
    connection.execute(
        """
        INSERT INTO agv (
            id, version, x, y, status, task_id, active_fault_event_id,
            edge_progress, motion_state, current_speed, target_speed, heading,
            motion_duration_ms, battery_level
        ) VALUES (901, 1, 2, 3, 'idle', NULL, NULL, 0, 'idle', 0, 0, 0, 0, 100)
        """
    )
    connection.commit()


def test_fresh_sqlite_upgrade_and_verify(sqlite_database: Path):
    result = upgrade_database()

    assert result["from_generation"] == "empty"
    assert result["revision"] == HEAD_REVISION
    assert result["backup"] is None
    verification = verify_database()
    assert verification["valid"] is True
    assert verification["integrity_check"] == "ok"


def test_unversioned_v2_schema_is_baselined_and_expanded(sqlite_database: Path):
    upgrade_database()
    connection = sqlite3.connect(str(sqlite_database))
    try:
        _seed_database(connection)
        connection.execute("PRAGMA foreign_keys=OFF")
        _drop_v3_foundation(connection)
        # These are the representative pre-beta columns previously added by
        # normal repository reads. Their values and both user/AGV rows must
        # survive the new Alembic-only upgrade path.
        for table_name, column_name in (
            ("agv", "scope_key"),
            ("agv", "version"),
            ("auth_user", "account_status"),
            ("auth_user", "must_change_password"),
        ):
            _drop_column(connection, table_name, column_name)
        connection.commit()
    finally:
        connection.close()
    dispose_engine()
    get_settings.cache_clear()

    result = upgrade_database()

    assert result["from_generation"] == "v2_unversioned"
    assert result["backup"] is not None
    assert result["record_counts_before"]["accounts"] == 1
    assert result["record_counts_before"]["agvs"] == 1
    assert result["record_counts_match"] is True
    assert verify_database()["valid"] is True
    connection = sqlite3.connect(str(sqlite_database))
    try:
        assert connection.execute("SELECT COUNT(*) FROM auth_user WHERE id = 'migration-user'").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM agv WHERE id = 901").fetchone()[0] == 1
        assert connection.execute("SELECT account_status FROM auth_user WHERE id = 'migration-user'").fetchone()[0] == "approved"
        assert connection.execute("SELECT must_change_password FROM auth_user WHERE id = 'migration-user'").fetchone()[0] == 0
        assert connection.execute("SELECT version FROM agv WHERE id = 901").fetchone()[0] == 1
    finally:
        connection.close()


def test_unversioned_beta_schema_is_stamped_then_upgraded(sqlite_database: Path):
    upgrade_database()
    connection = sqlite3.connect(str(sqlite_database))
    try:
        _drop_v3_foundation(connection)
        connection.commit()
    finally:
        connection.close()
    dispose_engine()
    get_settings.cache_clear()

    result = upgrade_database()

    assert result["from_generation"] == "v3_beta1_unversioned"
    assert verify_database()["valid"] is True


def test_sqlite_backup_verify_and_restore(sqlite_database: Path):
    upgrade_database()
    connection = sqlite3.connect(str(sqlite_database))
    try:
        _seed_database(connection)
    finally:
        connection.close()
    dispose_engine()
    get_settings.cache_clear()

    backup = backup_database()
    connection = sqlite3.connect(str(sqlite_database))
    try:
        connection.execute("UPDATE auth_user SET display_name = 'Changed after backup' WHERE id = 'migration-user'")
        connection.commit()
    finally:
        connection.close()

    restored = restore_database(backup["backup"], expected_sha256=backup["sha256"])

    assert restored["integrity_check"] == "ok"
    connection = sqlite3.connect(str(sqlite_database))
    try:
        display_name = connection.execute("SELECT display_name FROM auth_user WHERE id = 'migration-user'").fetchone()[0]
    finally:
        connection.close()
    assert display_name == "Before upgrade"
    assert verify_database()["valid"] is True


def test_restore_rejects_mismatched_checksum(sqlite_database: Path):
    upgrade_database()
    backup = backup_database()

    with pytest.raises(RuntimeError, match="checksum"):
        restore_database(backup["backup"], expected_sha256="0" * 64)
