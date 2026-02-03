"""add name column to expenses

Revision ID: d4e5f6a7b8c9
Revises: c8d9e0f1a2b3
Create Date: 2026-02-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "expenses",
        sa.Column("name", sa.String(100), nullable=False, server_default=""),
    )
    op.alter_column(
        "expenses",
        "name",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("expenses", "name")
