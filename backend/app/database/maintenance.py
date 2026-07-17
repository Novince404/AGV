from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from app.core.database import check_database_connection, dispose_engine, get_engine
from app.core.settings import get_settings


BASELINE_REVISION = "0001_beta1_baseline"
HEAD_REVISION = "0003_auth_password_change_flag"

# A database with these tables is recognisably an AGV v2/v3 predecessor.  We
# deliberately refuse to stamp arbitrary application databases.
KNOWN_LEGACY_TABLES = {"agv", "task", "map_layout", "auth_user"}
REQUIRED_CORE_TABLES = {
    "agv",
    "task",
    "map_layout",
    "map_profile",
    "auth_user",
    "auth_session",
    "fault_event",
    "ui_settings",
}
REQUIRED_FOUNDATION_TABLES = {
    "oidc_identity",
    "oidc_link_request",
    "runtime_event",
    "runtime_command",
    "scheduler_lease",
    "idempotency_record",
}
REQUIRED_COLUMNS: dict[str, set[str]] = {
    "agv": {"scope_key", "version", "battery_level"},
    "task": {"scope_key", "version"},
    "map_layout": {"scope_key", "version"},
    "map_profile": {"version"},
    "auth_user": {"account_status", "must_change_password"},
    "fault_event": {"scope_key"},
    "ui_settings": {"scope_key", "battery_charge_per_sec"},
}
INVENTORY_TABLES = {
    "accounts": "auth_user",
    "enterprise_applications": "enterprise_application",
    "agvs": "agv",
    "tasks": "task",
    "map_layouts": "map_layout",
    "map_profiles": "map_profile",
    "topology_nodes": "map_layout_topology_node",
    "topology_edges": "map_layout_topology_edge",
    "feedback": "platform_bug_feedback",
    "audit_events": "operation_audit",
}


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _alembic_config() -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
    return config


def _sqlite_path() -> Path:
    url = make_url(get_settings().database_url)
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        raise RuntimeError("This operation is available only for file-backed SQLite databases")
    return Path(url.database).expanduser().resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_revision() -> str | None:
    engine = get_engine()
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        return None
    with engine.connect() as connection:
        row = connection.exec_driver_sql("SELECT version_num FROM alembic_version").first()
    return str(row[0]) if row else None


def _schema_generation(tables: set[str], revision: str | None) -> str:
    if revision:
        return f"alembic:{revision}"
    if not tables:
        return "empty"
    if not KNOWN_LEGACY_TABLES.issubset(tables):
        return "unknown"
    if REQUIRED_FOUNDATION_TABLES.issubset(tables):
        return "v3_beta_unversioned"

    # Scope columns were added in the beta-era multi-tenant work. Their
    # absence identifies the earlier v2 shape without relying on row data.
    try:
        inspector = inspect(get_engine())
        agv_columns = {item["name"] for item in inspector.get_columns("agv")}
        auth_columns = {item["name"] for item in inspector.get_columns("auth_user")}
    except Exception:
        return "unknown"
    if "scope_key" in agv_columns and "account_status" in auth_columns:
        return "v3_beta1_unversioned"
    return "v2_unversioned"


def database_inventory() -> dict[str, int]:
    """Return durable record counts used to validate a no-loss upgrade."""
    settings = get_settings()
    if settings.data_backend == "memory":
        return {}
    engine = get_engine()
    available_tables = set(inspect(engine).get_table_names())
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for label, table_name in INVENTORY_TABLES.items():
            if table_name not in available_tables:
                continue
            # Both names originate from the static mapping above, rather than
            # from command input, so the identifier is safe to embed here.
            counts[label] = int(connection.exec_driver_sql(f"SELECT COUNT(*) FROM {table_name}").scalar_one())
    return counts


def _sqlite_integrity_check(path: Path) -> str:
    connection = sqlite3.connect(str(path))
    try:
        result = connection.execute("PRAGMA integrity_check").fetchall()
    finally:
        connection.close()
    messages = [str(row[0]) for row in result]
    if messages != ["ok"]:
        raise RuntimeError(f"SQLite integrity check failed: {'; '.join(messages)}")
    return "ok"


def _sqlite_backup(source: Path, target: Path) -> None:
    """Create a transactionally consistent SQLite copy, including WAL data."""
    if source.resolve() == target.resolve():
        raise RuntimeError("SQLite backup destination must differ from the source database")
    source_connection = sqlite3.connect(str(source))
    target_connection = sqlite3.connect(str(target))
    try:
        source_connection.backup(target_connection)
        target_connection.commit()
    finally:
        target_connection.close()
        source_connection.close()


def _sqlite_sidecars(path: Path) -> tuple[Path, Path, Path]:
    return (
        path.with_name(f"{path.name}-wal"),
        path.with_name(f"{path.name}-shm"),
        path.with_name(f"{path.name}-journal"),
    )


def _sqlite_has_application_tables(path: Path) -> bool:
    """Return whether a SQLite file contains user tables without changing it."""
    connection = sqlite3.connect(str(path))
    try:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' LIMIT 1"
        ).fetchone()
    finally:
        connection.close()
    return row is not None


def database_status() -> dict:
    settings = get_settings()
    connected, error_text = check_database_connection() if settings.data_backend != "memory" else (True, None)
    tables: list[str] = []
    revision = None
    inspect_error = None
    if connected and settings.data_backend != "memory":
        try:
            inspector = inspect(get_engine())
            tables = sorted(inspector.get_table_names())
            revision = _read_revision()
        except Exception as exc:  # pragma: no cover - driver/corruption diagnostic path
            inspect_error = str(exc)
            connected = False
            error_text = inspect_error
    table_set = set(tables)
    return {
        "backend": settings.data_backend,
        "connected": connected,
        "error": error_text,
        "revision": revision,
        "table_count": len(tables),
        "schema_generation": _schema_generation(table_set, revision) if connected else "unavailable",
        "legacy_schema_detected": bool(KNOWN_LEGACY_TABLES.issubset(table_set) and not revision),
        "record_counts": database_inventory() if connected and settings.data_backend != "memory" else {},
    }


def backup_database(destination: str | None = None) -> dict:
    settings = get_settings()
    if settings.data_backend != "sqlite":
        raise RuntimeError("MySQL backups must be created with the deployment's managed backup or mysqldump workflow")
    source = _sqlite_path()
    if not source.exists():
        raise FileNotFoundError(f"SQLite database does not exist: {source}")
    target = (
        Path(destination).expanduser().resolve()
        if destination
        else source.with_name(f"{source.stem}.{_utc_stamp()}.backup{source.suffix}")
    )
    if target.exists():
        raise FileExistsError(f"Backup destination already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    _sqlite_backup(source, target)
    integrity = _sqlite_integrity_check(target)
    return {
        "source": str(source),
        "backup": str(target),
        "sha256": sha256_file(target),
        "size": target.stat().st_size,
        "integrity_check": integrity,
        "revision": database_status().get("revision"),
    }


def upgrade_database(*, mysql_backup_confirmed: bool = False) -> dict:
    settings = get_settings()
    if settings.data_backend == "memory":
        raise RuntimeError("Memory mode does not have a database schema")
    if settings.data_backend == "mysql" and not mysql_backup_confirmed:
        raise RuntimeError("Create and verify a MySQL backup, then pass --backup-confirmed")

    # Close pooled SQLite handles before the migration and make a consistent
    # backup before *any* schema change. Fresh files deliberately have no
    # backup because there is no user data to preserve yet.
    dispose_engine()
    inspector = inspect(get_engine())
    tables = set(inspector.get_table_names())
    revision = _read_revision()
    generation = _schema_generation(tables, revision)
    if revision == HEAD_REVISION:
        result = database_status()
        result["backup"] = None
        result["from_generation"] = generation
        result["target_revision"] = HEAD_REVISION
        return result

    counts_before = database_inventory()
    sqlite_source = _sqlite_path() if settings.data_backend == "sqlite" else None
    backup = (
        backup_database()
        if sqlite_source and sqlite_source.exists() and sqlite_source.stat().st_size and _sqlite_has_application_tables(sqlite_source)
        else None
    )
    config = _alembic_config()
    if tables and revision is None:
        if generation == "unknown":
            raise RuntimeError("Unknown unversioned database schema; automatic stamping was refused")
        command.stamp(config, BASELINE_REVISION)
    command.upgrade(config, "head")
    dispose_engine()
    result = database_status()
    result["backup"] = backup
    result["from_generation"] = generation
    result["target_revision"] = HEAD_REVISION
    result["record_counts_before"] = counts_before
    result["record_counts_after"] = database_inventory()
    result["record_counts_match"] = all(
        result["record_counts_after"].get(label) == count
        for label, count in result["record_counts_before"].items()
    )
    return result


def _missing_required_columns(table_names: set[str]) -> dict[str, list[str]]:
    inspector = inspect(get_engine())
    missing: dict[str, list[str]] = {}
    for table_name, required_columns in REQUIRED_COLUMNS.items():
        if table_name not in table_names:
            continue
        present = {column["name"] for column in inspector.get_columns(table_name)}
        absent = sorted(required_columns - present)
        if absent:
            missing[table_name] = absent
    return missing


def verify_database() -> dict:
    status = database_status()
    if not status["connected"]:
        return {
            **status,
            "valid": False,
            "missing_tables": sorted(REQUIRED_CORE_TABLES | REQUIRED_FOUNDATION_TABLES),
            "missing_columns": REQUIRED_COLUMNS,
            "integrity_check": None,
        }
    if status["backend"] == "memory":
        return {**status, "valid": True, "missing_tables": [], "missing_columns": {}, "integrity_check": "not-applicable"}
    table_names = set(inspect(get_engine()).get_table_names())
    missing_tables = sorted((REQUIRED_CORE_TABLES | REQUIRED_FOUNDATION_TABLES) - table_names)
    missing_columns = _missing_required_columns(table_names)
    integrity = "not-applicable"
    integrity_error = None
    if status["backend"] == "sqlite":
        try:
            integrity = _sqlite_integrity_check(_sqlite_path())
        except Exception as exc:
            integrity_error = str(exc)
    valid = (
        not missing_tables
        and not missing_columns
        and status["revision"] == HEAD_REVISION
        and integrity_error is None
    )
    return {
        **status,
        "valid": valid,
        "missing_tables": missing_tables,
        "missing_columns": missing_columns,
        "integrity_check": integrity,
        "integrity_error": integrity_error,
    }


def restore_database(backup_path: str, expected_sha256: str | None = None) -> dict:
    target = _sqlite_path()
    backup = Path(backup_path).expanduser().resolve()
    if not backup.is_file():
        raise FileNotFoundError(f"Backup does not exist: {backup}")
    actual_sha256 = sha256_file(backup)
    if expected_sha256 and actual_sha256.lower() != expected_sha256.lower():
        raise RuntimeError("Backup checksum does not match the expected SHA-256")
    source_integrity = _sqlite_integrity_check(backup)
    dispose_engine()
    target.parent.mkdir(parents=True, exist_ok=True)
    # A stale WAL can be replayed after the main file is restored. It contains
    # only the pre-restore database journal and must not survive this explicit
    # restore operation.
    for sidecar in _sqlite_sidecars(target):
        if sidecar.exists():
            sidecar.unlink()
    _sqlite_backup(backup, target)
    target_integrity = _sqlite_integrity_check(target)
    return {
        "restored": str(target),
        "source": str(backup),
        "sha256": actual_sha256,
        "source_integrity_check": source_integrity,
        "integrity_check": target_integrity,
    }


def print_result(result: dict) -> None:
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
