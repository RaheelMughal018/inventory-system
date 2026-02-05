"""add production batch stage (draft, in_process, ready) and updated_at

Revision ID: h3c4d5e6f7g8
Revises: f1a2b3c4d5e6
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h3c4d5e6f7g8"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    production_stage = sa.Enum("DRAFT", "IN_PROCESS", "READY", name="productionstage")
    production_stage.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "production_batches",
        sa.Column("stage", production_stage, nullable=False, server_default="DRAFT"),
    )
    op.add_column(
        "production_batches",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    # Existing rows (created before stage existed) were completed runs → set to READY
    op.execute("UPDATE production_batches SET stage = 'READY'")


def downgrade() -> None:
    op.drop_column("production_batches", "updated_at")
    op.drop_column("production_batches", "stage")
    sa.Enum(name="productionstage").drop(op.get_bind(), checkfirst=True)