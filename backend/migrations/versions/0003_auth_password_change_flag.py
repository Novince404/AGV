"""Add the first-login password-change marker.

Revision ID: 0003_auth_password_change_flag
Revises: 0002_enterprise_foundation
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0003_auth_password_change_flag"
down_revision: Union[str, Sequence[str], None] = "0002_enterprise_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "auth_user" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("auth_user")}
    if "must_change_password" not in columns:
        # The persistent server default keeps old rows usable until the auth
        # service selects the appropriate policy for them. New accounts can be
        # explicitly marked true by the application without a data rewrite.
        op.add_column(
            "auth_user",
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )


def downgrade() -> None:
    # Expand-only migration: recovery uses a verified pre-upgrade backup.
    pass
