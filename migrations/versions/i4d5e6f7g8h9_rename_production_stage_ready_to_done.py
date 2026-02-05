"""rename production stage READY to DONE

Revision ID: i4d5e6f7g8h9
Revises: h3c4d5e6f7g8
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op


revision: str = "i4d5e6f7g8h9"
down_revision: Union[str, Sequence[str], None] = "h3c4d5e6f7g8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add DONE to the enum (PostgreSQL). Must commit before using new value in same session.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE productionstage ADD VALUE IF NOT EXISTS 'DONE'")
    # Migrate existing READY rows to DONE
    op.execute("UPDATE production_batches SET stage = 'DONE'::productionstage WHERE stage::text = 'READY'")


def downgrade() -> None:
    # Revert DONE back to READY (DONE remains in enum; PostgreSQL cannot remove enum values easily)
    op.execute("UPDATE production_batches SET stage = 'READY'::productionstage WHERE stage::text = 'DONE'")
