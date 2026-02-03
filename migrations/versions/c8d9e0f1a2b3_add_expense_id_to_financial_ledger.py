"""add expense_id to financial_ledger (relation expenses <-> financial_ledger)

Revision ID: c8d9e0f1a2b3
Revises: be77405e90e6
Create Date: 2026-02-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "be77405e90e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "financial_ledger",
        sa.Column("expense_id", sa.String(20), sa.ForeignKey("expenses.id"), nullable=True),
    )
    op.create_index("ix_financial_ledger_expense_id", "financial_ledger", ["expense_id"])


def downgrade() -> None:
    op.drop_index("ix_financial_ledger_expense_id", table_name="financial_ledger")
    op.drop_column("financial_ledger", "expense_id")
