"""add production batch recipe items

Revision ID: j5e6f7g8h9i0
Revises: i4d5e6f7g8h9
Create Date: 2026-02-05 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'j5e6f7g8h9i0'
down_revision = 'i4d5e6f7g8h9'
branch_labels = None
depends_on = None


def upgrade():
    # Create production_batch_recipe_items table to store recipe snapshot per batch
    op.create_table('production_batch_recipe_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('production_batch_id', sa.String(length=30), nullable=False),
        sa.Column('raw_item_id', sa.String(length=10), nullable=False),
        sa.Column('quantity_per_unit', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.ForeignKeyConstraint(['production_batch_id'], ['production_batches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['raw_item_id'], ['items.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_production_batch_recipe_items_production_batch_id'), 'production_batch_recipe_items', ['production_batch_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_production_batch_recipe_items_production_batch_id'), table_name='production_batch_recipe_items')
    op.drop_table('production_batch_recipe_items')
