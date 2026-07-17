"""Add legacy compatibility and enterprise runtime foundations.

Revision ID: 0002_enterprise_foundation
Revises: 0001_beta1_baseline
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.repositories.sql_models import (
    IdempotencyRecordEntity,
    OIDCIdentityEntity,
    OIDCLinkRequestEntity,
    RuntimeCommandEntity,
    RuntimeEventEntity,
    SchedulerLeaseEntity,
)


revision: str = "0002_enterprise_foundation"
down_revision: Union[str, Sequence[str], None] = "0001_beta1_baseline"
branch_labels = None
depends_on = None


FOUNDATION_TABLES = (
    OIDCIdentityEntity.__table__,
    OIDCLinkRequestEntity.__table__,
    RuntimeEventEntity.__table__,
    RuntimeCommandEntity.__table__,
    SchedulerLeaseEntity.__table__,
    IdempotencyRecordEntity.__table__,
)


def _add_version_column(table_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if "version" not in columns:
        op.add_column(table_name, sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    """Apply an expand-only compatibility change for an existing legacy table.

    The pre-Alembic application used repository-level ``ALTER TABLE`` calls.
    Keeping those changes here makes upgrades repeatable and ensures normal
    reads and writes never mutate the schema.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns(table_name)}
    if column.name not in columns:
        op.add_column(table_name, column)


def _upgrade_legacy_v2_columns() -> None:
    # These are all former repository-side compatibility alterations. Defaults
    # remain on disk deliberately: v3 follows expand/contract migrations and
    # does not remove or rewrite historic data during an upgrade.
    column_specs: dict[str, tuple[sa.Column, ...]] = {
        "agv": (
            sa.Column("scope_key", sa.String(length=128), nullable=True),
            sa.Column("render_x", sa.Float(), nullable=True),
            sa.Column("render_y", sa.Float(), nullable=True),
            sa.Column("current_node", sa.String(length=128), nullable=True),
            sa.Column("current_edge", sa.String(length=128), nullable=True),
            sa.Column("edge_progress", sa.Float(), nullable=False, server_default="0"),
            sa.Column("motion_state", sa.String(length=32), nullable=False, server_default="idle"),
            sa.Column("current_speed", sa.Float(), nullable=False, server_default="0"),
            sa.Column("target_speed", sa.Float(), nullable=False, server_default="0"),
            sa.Column("heading", sa.Float(), nullable=False, server_default="0"),
            sa.Column("motion_started_at", sa.String(length=32), nullable=True),
            sa.Column("motion_updated_at", sa.String(length=32), nullable=True),
            sa.Column("motion_duration_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("motion_source_x", sa.Float(), nullable=True),
            sa.Column("motion_source_y", sa.Float(), nullable=True),
            sa.Column("motion_target_x", sa.Float(), nullable=True),
            sa.Column("motion_target_y", sa.Float(), nullable=True),
            sa.Column("battery_level", sa.Float(), nullable=False, server_default="100"),
            sa.Column("energy_updated_at", sa.String(length=32), nullable=True),
            sa.Column("idle_since_at", sa.String(length=32), nullable=True),
            sa.Column("charge_started_at", sa.String(length=32), nullable=True),
            sa.Column("auto_target_node", sa.String(length=128), nullable=True),
            sa.Column("auto_target_type", sa.String(length=32), nullable=True),
        ),
        "auth_user": (
            sa.Column("account_status", sa.String(length=32), nullable=False, server_default="approved"),
            sa.Column("organization_id", sa.String(length=64), nullable=True),
            sa.Column("organization_name", sa.String(length=128), nullable=True),
            sa.Column("suspension_reason", sa.Text(), nullable=True),
            sa.Column("suspension_note", sa.Text(), nullable=True),
            sa.Column("suspended_at", sa.String(length=32), nullable=True),
            sa.Column("suspended_until", sa.String(length=32), nullable=True),
            sa.Column("suspended_by", sa.String(length=64), nullable=True),
            sa.Column("deactivated_at", sa.String(length=32), nullable=True),
            sa.Column("deactivated_by", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.String(length=32), nullable=True),
            sa.Column("last_login_at", sa.String(length=32), nullable=True),
            sa.Column("governance_updated_at", sa.String(length=32), nullable=True),
        ),
        "fault_event": (
            sa.Column("scope_key", sa.String(length=128), nullable=True),
        ),
        "map_layout": (
            sa.Column("scope_key", sa.String(length=128), nullable=True),
        ),
        "map_layout_topology_node": (
            sa.Column("capacity", sa.Integer(), nullable=False, server_default="1"),
        ),
        "map_profile_topology_node": (
            sa.Column("capacity", sa.Integer(), nullable=False, server_default="1"),
        ),
        "task": (
            sa.Column("scope_key", sa.String(length=128), nullable=True),
        ),
        "ui_settings": (
            sa.Column("scope_key", sa.String(length=128), nullable=True),
            sa.Column("show_topology_edge_speed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("show_runtime_segment_type", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("show_runtime_conflict_reason", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("show_selected_agv_runtime_overlay", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("show_business_points", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("base_speed", sa.Float(), nullable=False, server_default=sa.text("1.11")),
            sa.Column("follow_distance", sa.Float(), nullable=False, server_default=sa.text("0.75")),
            sa.Column("deadlock_timeout_sec", sa.Float(), nullable=False, server_default=sa.text("4.5")),
            sa.Column("idle_return_timeout_sec", sa.Float(), nullable=False, server_default=sa.text("12")),
            sa.Column("idle_charge_timeout_sec", sa.Float(), nullable=False, server_default=sa.text("45")),
            sa.Column("idle_charge_battery_threshold", sa.Float(), nullable=False, server_default=sa.text("60")),
            sa.Column("low_battery_threshold", sa.Float(), nullable=False, server_default=sa.text("24")),
            sa.Column("battery_active_drain_per_sec", sa.Float(), nullable=False, server_default=sa.text("0.16")),
            sa.Column("battery_waiting_drain_per_sec", sa.Float(), nullable=False, server_default=sa.text("0.05")),
            sa.Column("battery_idle_drain_per_sec", sa.Float(), nullable=False, server_default=sa.text("0.01")),
            sa.Column("battery_parking_idle_drain_per_sec", sa.Float(), nullable=False, server_default=sa.text("0.003")),
            sa.Column("battery_charge_per_sec", sa.Float(), nullable=False, server_default=sa.text("6")),
        ),
    }
    for table_name, columns in column_specs.items():
        for column in columns:
            _add_column_if_missing(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()
    for table in FOUNDATION_TABLES:
        table.create(bind=bind, checkfirst=True)
    _upgrade_legacy_v2_columns()
    for table_name in ("agv", "task", "map_layout", "map_profile"):
        _add_version_column(table_name)


def downgrade() -> None:
    # Enterprise migrations use expand/contract semantics. Downgrade never
    # removes user data; restore a pre-upgrade backup for a full rollback.
    pass
