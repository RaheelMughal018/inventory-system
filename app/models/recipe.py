"""
Production / Manufacturing models: Recipe, RecipeItem, ProductionBatch, ProductionSerial.
Links final products to raw materials with quantities; tracks production runs and serial numbers.
Production batches have stages: DRAFT (recipe editable), IN_PROCESS (recipe editable), DONE (production complete; recipe not editable).
"""

import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.item_category import generate_custom_id


class ProductionStage(str, enum.Enum):
    """Production batch lifecycle. Recipe can be edited only when no batch for that product is DONE."""

    DRAFT = "DRAFT"           # Created, no inventory moved; recipe editable
    IN_PROCESS = "IN_PROCESS" # Execution in progress; recipe editable
    DONE = "DONE"             # Production complete; recipe not editable


class Recipe(Base):
    """One recipe per final product. Defines which raw items and how much per unit."""

    __tablename__ = "recipes"

    id = Column(String(20), primary_key=True, default=lambda: generate_custom_id("RCP"))
    final_product_id = Column(
        String(10),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    name = Column(String(200), nullable=True)  # optional display name, e.g. "Noodles Recipe"

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    final_product = relationship("Item", foreign_keys=[final_product_id])
    recipe_items = relationship(
        "RecipeItem",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class RecipeItem(Base):
    """
    Raw item required per 1 unit of final product.
    quantity_per_unit = units of this raw item needed per 1 unit of final product (e.g. 4 wheels per 1 car).
    Cost for this line per 1 final = quantity_per_unit × raw item's avg_price (e.g. 4 × 90 = 360).
    The same raw item can appear multiple times; production aggregates by raw_item_id and sums quantities.
    """

    __tablename__ = "recipe_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(String(20), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    raw_item_id = Column(String(10), ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    quantity_per_unit = Column(Numeric(15, 4), nullable=False)  # e.g. 4 wheels per 1 car; cost = this × raw.avg_price

    recipe = relationship("Recipe", back_populates="recipe_items")
    raw_item = relationship("Item", foreign_keys=[raw_item_id])


class ProductionBatch(Base):
    """
    One batch of production: N units of a final product.
    Stage: DRAFT (no inventory moved, recipe editable) → IN_PROCESS (executing, recipe editable) → DONE (production complete, recipe not editable).
    Final product quantity is increased only when batch moves to DONE (on execute).
    Each batch has its own recipe snapshot (batch_recipe_items) that can be modified independently of the master recipe.
    """

    __tablename__ = "production_batches"

    id = Column(String(30), primary_key=True, default=lambda: generate_custom_id("PROD", length=8))
    final_product_id = Column(String(10), ForeignKey("items.id", ondelete="RESTRICT"), nullable=False)
    quantity_produced = Column(Integer, nullable=False)
    stage = Column(Enum(ProductionStage), nullable=False, default=ProductionStage.DRAFT, server_default="DRAFT")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    final_product = relationship("Item", foreign_keys=[final_product_id])
    serials = relationship(
        "ProductionSerial",
        back_populates="production_batch",
        cascade="all, delete-orphan",
    )
    batch_recipe_items = relationship(
        "ProductionBatchRecipeItem",
        back_populates="production_batch",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class ProductionSerial(Base):
    """One serial number per produced unit. User-assigned, prefix LEH-."""

    __tablename__ = "production_serials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    production_batch_id = Column(
        String(30),
        ForeignKey("production_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    serial_number = Column(String(50), unique=True, nullable=False)
    final_product_id = Column(String(10), ForeignKey("items.id", ondelete="RESTRICT"), nullable=False)

    production_batch = relationship("ProductionBatch", back_populates="serials")
    final_product = relationship("Item", foreign_keys=[final_product_id])


class ProductionBatchRecipeItem(Base):
    """
    Recipe snapshot for a specific production batch. This is a copy of the master recipe
    that can be modified independently for this batch only. Created when batch is in DRAFT,
    can be modified in DRAFT stage only (before execution).
    """

    __tablename__ = "production_batch_recipe_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    production_batch_id = Column(
        String(30),
        ForeignKey("production_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_item_id = Column(String(10), ForeignKey("items.id", ondelete="RESTRICT"), nullable=False)
    quantity_per_unit = Column(Numeric(15, 4), nullable=False)

    production_batch = relationship("ProductionBatch", back_populates="batch_recipe_items")
    raw_item = relationship("Item", foreign_keys=[raw_item_id])
