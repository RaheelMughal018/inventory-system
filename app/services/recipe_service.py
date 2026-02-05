"""
Recipe service: CRUD for recipes and recipe items.
Validates final product is FINAL_PRODUCT and raw items are RAW_MATERIAL.
"""

from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.logger_config import logger
from app.models.item_category import Item, ItemType, generate_custom_id
from app.models.recipe import ProductionStage, Recipe, RecipeItem
from app.services.item_service import get_item_by_id


def has_production_done(db: Session, final_product_id: str) -> bool:
    """True if any production batch for this final product is DONE (recipe cannot be edited)."""
    from app.models.recipe import ProductionBatch
    return (
        db.query(ProductionBatch)
        .filter(
            ProductionBatch.final_product_id == final_product_id,
            ProductionBatch.stage == ProductionStage.DONE,
        )
        .limit(1)
        .first()
        is not None
    )


def _validate_final_product(db: Session, item_id: str) -> Item:
    item = get_item_by_id(db, item_id)
    if not item:
        raise ValueError(f"Item not found: {item_id}")
    if item.type != ItemType.FINAL_PRODUCT:
        raise ValueError(f"Item {item_id} must be type FINAL_PRODUCT, got {item.type.value}")
    return item


def _validate_raw_item(db: Session, item_id: str) -> Item:
    item = get_item_by_id(db, item_id)
    if not item:
        raise ValueError(f"Item not found: {item_id}")
    if item.type != ItemType.RAW_MATERIAL:
        raise ValueError(f"Item {item_id} must be type RAW_MATERIAL, got {item.type.value}")
    return item


def _generate_recipe_id(db: Session) -> str:
    for _ in range(10):
        rid = generate_custom_id("RCP")
        if db.query(Recipe).filter(Recipe.id == rid).first() is None:
            return rid
    raise ValueError("Failed to generate unique recipe ID")


def _calculate_and_update_final_product_price(db: Session, recipe: Recipe) -> None:
    """
    Calculate total cost of raw materials for this recipe and update the final product's avg_price.
    Cost per unit = sum of (quantity_per_unit × raw_item.avg_price) for all recipe items.
    This represents the standard cost to produce one unit of the final product.
    """
    total_cost = Decimal("0.00")
    
    # Recipe items should already be loaded via joinedload, but fetch them if needed
    recipe_items = recipe.recipe_items
    if not recipe_items:
        recipe_items = (
            db.query(RecipeItem)
            .options(joinedload(RecipeItem.raw_item))
            .filter(RecipeItem.recipe_id == recipe.id)
            .all()
        )
    
    for recipe_item in recipe_items:
        raw_item = recipe_item.raw_item
        if not raw_item:
            raw_item = get_item_by_id(db, recipe_item.raw_item_id)
        
        quantity_per_unit = Decimal(str(recipe_item.quantity_per_unit))
        raw_avg_price = raw_item.avg_price or Decimal("0.00")
        line_cost = quantity_per_unit * raw_avg_price
        total_cost += line_cost
    
    # Update final product's avg_price
    final_product = db.query(Item).filter(Item.id == recipe.final_product_id).first()
    if final_product:
        final_product.avg_price = total_cost
        db.add(final_product)
        logger.info(
            f"Updated final product {recipe.final_product_id} avg_price to {total_cost} "
            f"(recipe cost per unit)"
        )


def create_recipe(
    db: Session,
    final_product_id: str,
    items: List[dict],
    name: Optional[str] = None,
) -> Recipe:
    """
    Create a recipe for a final product.
    items: list of {"raw_item_id": str, "quantity_per_unit": Decimal}.
    The same raw item can appear multiple times (quantities are aggregated in production).
    """
    _validate_final_product(db, final_product_id)

    for it in items:
        _validate_raw_item(db, it["raw_item_id"])
        q = it["quantity_per_unit"]
        if q is None or (isinstance(q, (int, float, Decimal)) and q <= 0):
            raise ValueError(f"quantity_per_unit must be positive for {it['raw_item_id']}")

    existing = db.query(Recipe).filter(Recipe.final_product_id == final_product_id).first()
    if existing:
        raise ValueError(f"Recipe already exists for final product {final_product_id}")

    recipe_id = _generate_recipe_id(db)
    recipe = Recipe(
        id=recipe_id,
        final_product_id=final_product_id,
        name=name,
    )
    db.add(recipe)
    db.flush()

    for it in items:
        ri = RecipeItem(
            recipe_id=recipe.id,
            raw_item_id=it["raw_item_id"],
            quantity_per_unit=Decimal(str(it["quantity_per_unit"])),
        )
        db.add(ri)
    
    db.flush()  # Flush to get recipe items IDs
    
    # Calculate and set final product's avg_price based on recipe cost
    _calculate_and_update_final_product_price(db, recipe)

    try:
        db.commit()
        db.refresh(recipe)
        logger.info(f"Recipe created: {recipe.id} for final product {final_product_id}")
        return recipe
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Recipe create integrity error: {e}")
        raise ValueError("Failed to create recipe (duplicate or constraint).")


def get_recipe_by_id(db: Session, recipe_id: str) -> Optional[Recipe]:
    return (
        db.query(Recipe)
        .options(
            joinedload(Recipe.final_product),
            joinedload(Recipe.recipe_items).joinedload(RecipeItem.raw_item),
        )
        .filter(Recipe.id == recipe_id)
        .first()
    )


def get_recipe_by_final_product_id(db: Session, final_product_id: str) -> Optional[Recipe]:
    return (
        db.query(Recipe)
        .options(
            joinedload(Recipe.final_product),
            joinedload(Recipe.recipe_items).joinedload(RecipeItem.raw_item),
        )
        .filter(Recipe.final_product_id == final_product_id)
        .first()
    )


def get_all_recipes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
) -> Tuple[List[Recipe], int]:
    query = db.query(Recipe).options(
        joinedload(Recipe.final_product),
        joinedload(Recipe.recipe_items).joinedload(RecipeItem.raw_item),
    )
    if search:
        term = f"%{search}%"
        query = query.join(Recipe.final_product).filter(
            Item.name.ilike(term) | Item.id.ilike(term)
        )
    total = query.count()
    recipes = query.order_by(Recipe.created_at.desc()).offset(skip).limit(limit).all()
    return recipes, total


def update_recipe(
    db: Session,
    recipe_id: str,
    name: Optional[str] = None,
    items: Optional[List[dict]] = None,
) -> Optional[Recipe]:
    recipe = get_recipe_by_id(db, recipe_id)
    if not recipe:
        return None

    if has_production_done(db, recipe.final_product_id):
        raise ValueError(
            "Cannot edit recipe when production is in DONE stage for this product. "
            "Recipe can be edited when production is in DRAFT or IN_PROCESS stage only."
        )

    if name is not None:
        recipe.name = name

    if items is not None:
        for it in items:
            _validate_raw_item(db, it["raw_item_id"])
            q = it["quantity_per_unit"]
            if q is None or (isinstance(q, (int, float, Decimal)) and q <= 0):
                raise ValueError(f"quantity_per_unit must be positive for {it['raw_item_id']}")

        db.query(RecipeItem).filter(RecipeItem.recipe_id == recipe_id).delete()
        for it in items:
            ri = RecipeItem(
                recipe_id=recipe.id,
                raw_item_id=it["raw_item_id"],
                quantity_per_unit=Decimal(str(it["quantity_per_unit"])),
            )
            db.add(ri)
        
        db.flush()  # Flush to get new recipe items
        
        # Recalculate and update final product's avg_price based on new recipe cost
        _calculate_and_update_final_product_price(db, recipe)

    try:
        db.commit()
        db.refresh(recipe)
        logger.info(f"Recipe updated: {recipe_id}")
        return recipe
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Recipe update integrity error: {e}")
        raise ValueError("Failed to update recipe.")


def delete_recipe(db: Session, recipe_id: str) -> bool:
    recipe = get_recipe_by_id(db, recipe_id)
    if not recipe:
        return False

    if has_production_done(db, recipe.final_product_id):
        raise ValueError(
            "Cannot delete recipe when production is in DONE stage for this product. "
            "Recipe can be edited when production is in DRAFT or IN_PROCESS stage only."
        )

    try:
        db.delete(recipe)
        db.commit()
        logger.info(f"Recipe deleted: {recipe_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Recipe delete error: {e}")
        raise ValueError("Failed to delete recipe.")
