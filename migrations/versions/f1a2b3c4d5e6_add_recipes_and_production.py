"""add recipes and production tables

Revision ID: f1a2b3c4d5e6
Revises: d4e5f6a7b8c9
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recipes",
        sa.Column("id", sa.String(length=20), nullable=False),
        sa.Column("final_product_id", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["final_product_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("final_product_id"),
    )

    op.create_table(
        "recipe_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipe_id", sa.String(length=20), nullable=False),
        sa.Column("raw_item_id", sa.String(length=10), nullable=False),
        sa.Column("quantity_per_unit", sa.Numeric(precision=15, scale=4), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id", "raw_item_id", name="uq_recipe_raw_item"),
    )

    op.create_table(
        "production_batches",
        sa.Column("id", sa.String(length=30), nullable=False),
        sa.Column("final_product_id", sa.String(length=10), nullable=False),
        sa.Column("quantity_produced", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["final_product_id"], ["items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "production_serials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("production_batch_id", sa.String(length=30), nullable=False),
        sa.Column("serial_number", sa.String(length=50), nullable=False),
        sa.Column("final_product_id", sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(["production_batch_id"], ["production_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["final_product_id"], ["items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("serial_number"),
    )

    op.create_index(op.f("ix_production_serials_serial_number"), "production_serials", ["serial_number"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_production_serials_serial_number"), table_name="production_serials")
    op.drop_table("production_serials")
    op.drop_table("production_batches")
    op.drop_table("recipe_items")
    op.drop_table("recipes")
