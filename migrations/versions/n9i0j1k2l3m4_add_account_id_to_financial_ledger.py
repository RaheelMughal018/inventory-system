"""add account_id to financial_ledger

Revision ID: n9i0j1k2l3m4
Revises: m8h9i0j1k2l3
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa

revision = 'n9i0j1k2l3m4'
down_revision = 'm8h9i0j1k2l3'
branch_labels = None
depends_on = None


def upgrade():
    # Add account_id column to financial_ledger table
    op.add_column(
        'financial_ledger',
        sa.Column('account_id', sa.String(length=20), nullable=True)
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_financial_ledger_account_id',
        'financial_ledger',
        'payment_accounts',
        ['account_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create index for better query performance
    op.create_index(
        'ix_financial_ledger_account_id',
        'financial_ledger',
        ['account_id']
    )


def downgrade():
    # Remove index
    op.drop_index('ix_financial_ledger_account_id', table_name='financial_ledger')
    
    # Remove foreign key constraint
    op.drop_constraint('fk_financial_ledger_account_id', 'financial_ledger', type_='foreignkey')
    
    # Remove column
    op.drop_column('financial_ledger', 'account_id')
