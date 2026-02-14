"""add account opening_balance and account_ledger

Revision ID: l7g8h9i0j1k2
Revises: k6f7g8h9i0j1
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa

revision = 'l7g8h9i0j1k2'
down_revision = 'k6f7g8h9i0j1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'payment_accounts',
        sa.Column('opening_balance', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0.00')
    )
    op.create_table(
        'account_ledger',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_id', sa.String(length=20), nullable=False),
        sa.Column('ref_type', sa.String(length=30), nullable=False),
        sa.Column('ref_id', sa.String(length=50), nullable=True),
        sa.Column('debit', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('credit', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['payment_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_account_ledger_account_id'), 'account_ledger', ['account_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_account_ledger_account_id'), table_name='account_ledger')
    op.drop_table('account_ledger')
    op.drop_column('payment_accounts', 'opening_balance')
