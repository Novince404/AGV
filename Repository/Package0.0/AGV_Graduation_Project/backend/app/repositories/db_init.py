from __future__ import annotations

from sqlalchemy import inspect, text

from app.core.database import get_engine
from app.repositories.sql_models import Base


_schema_compatibility_checked = False
_SCOPED_ID_VARCHAR_LENGTH = 191
_SCOPED_ID_COLUMNS: tuple[tuple[str, str, bool], ...] = (
    ("map_preset_cell", "preset_id", False),
    ("map_preset_valid_cell", "preset_id", False),
    ("map_preset", "id", False),
    ("map_profile_cell", "profile_id", False),
    ("map_profile_valid_cell", "profile_id", False),
    ("map_profile_topology_node", "profile_id", False),
    ("map_profile_topology_edge", "profile_id", False),
    ("map_profile", "id", False),
    ("task_template_stage", "template_id", False),
    ("task_template", "id", False),
    ("point_library", "id", False),
)


def _ensure_scoped_string_id_capacity() -> None:
    engine = get_engine()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    ddl_statements: list[str] = []

    for table_name, column_name, nullable in _SCOPED_ID_COLUMNS:
        if table_name not in table_names:
            continue
        columns = {column["name"]: column for column in inspector.get_columns(table_name)}
        column = columns.get(column_name)
        if column is None:
            continue
        current_length = getattr(column["type"], "length", None)
        if isinstance(current_length, int) and current_length >= _SCOPED_ID_VARCHAR_LENGTH:
            continue
        null_sql = "NULL" if nullable else "NOT NULL"
        ddl_statements.append(
            f"ALTER TABLE {table_name} MODIFY COLUMN {column_name} VARCHAR({_SCOPED_ID_VARCHAR_LENGTH}) {null_sql}"
        )

    if not ddl_statements:
        return

    with engine.begin() as connection:
        is_mysql = connection.dialect.name.startswith("mysql")
        if is_mysql:
            connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        try:
            for statement in ddl_statements:
                connection.execute(text(statement))
        finally:
            if is_mysql:
                connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def create_all_tables() -> None:
    global _schema_compatibility_checked
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    if _schema_compatibility_checked:
        return
    _ensure_scoped_string_id_capacity()
    _schema_compatibility_checked = True

