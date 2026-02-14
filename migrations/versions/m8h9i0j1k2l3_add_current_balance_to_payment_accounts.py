"""add current_balance to payment_accounts

Revision ID: m8h9i0j1k2l3
Revises: l7g8h9i0j1k2
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa

revision = 'm8h9i0j1k2l3'
down_revision = 'l7g8h9i0j1k2'
branch_labels = None
depends_on = None


def upgrade():
    # Add current_balance column with default value of 0
    op.add_column(
        'payment_accounts',
        sa.Column('current_balance', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00')
    )
    
    # Set current_balance = opening_balance for existing accounts
    op.execute("""
        UPDATE payment_accounts 
        SET current_balance = COALESCE(opening_balance, 0.00)
    """)


def downgrade():
    op.drop_column('payment_accounts', 'current_balance')
