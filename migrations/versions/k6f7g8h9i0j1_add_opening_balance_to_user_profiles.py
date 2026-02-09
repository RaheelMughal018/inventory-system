"""add opening balance to user profiles

Revision ID: k6f7g8h9i0j1
Revises: j5e6f7g8h9i0
Create Date: 2026-02-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'k6f7g8h9i0j1'
down_revision = 'j5e6f7g8h9i0'
branch_labels = None
depends_on = None


def upgrade():
    # Add opening_balance and opening_balance_type columns to user_profiles table
    op.add_column('user_profiles', 
        sa.Column('opening_balance', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0.00')
    )
    op.add_column('user_profiles',
        sa.Column('opening_balance_type', sa.String(length=10), nullable=True, server_default='DEBIT')
    )


def downgrade():
    # Remove opening_balance and opening_balance_type columns from user_profiles table
    op.drop_column('user_profiles', 'opening_balance_type')
    op.drop_column('user_profiles', 'opening_balance')
