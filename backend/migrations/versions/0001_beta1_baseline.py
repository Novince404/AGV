"""Establish the v3 beta.1 schema baseline.

Revision ID: 0001_beta1_baseline
Revises:
"""
from typing import Sequence, Union

from alembic import op

from app.repositories.sql_models import Base


revision: str = "0001_beta1_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fresh installs receive the complete legacy schema. Existing beta databases
    # are validated and stamped at this revision by the maintenance command.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # The baseline is intentionally non-destructive. Restores use a verified
    # database backup instead of dropping application data.
    pass
