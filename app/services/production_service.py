"""
Production service: preview, feasibility check, and execution.
Uses recipes to consume raw items and produce final products with serial numbers.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.logger_config import logger
from app.models.item_category import Item, ItemType, generate_custom_id
from app.models.recipe import ProductionBatch, ProductionBatchRecipeItem, ProductionSerial, ProductionStage, Recipe, RecipeItem
from app.models.stock import Stock
from app.services.item_service import get_item_by_id
from app.services.recipe_service import get_recipe_by_final_product_id


REF_TYPE_PRODUCTION = "PRODUCTION"


def _generate_unique_id(db: Session, prefix: str, model_class: type, length: int = 5) -> str:
    for _ in range(15):
        new_id = generate_custom_id(prefix, length=length)
        if db.query(model_class).filter(model_class.id == new_id).first() is None:
            return new_id
    raise ValueError(f"Failed to generate unique {prefix} ID")


def _aggregate_recipe_by_raw_item(recipe_items) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate recipe_items by raw_item_id: sum quantity_per_unit per raw item.
    Works with both Recipe.recipe_items and ProductionBatch.batch_recipe_items.
    Returns dict[raw_item_id] = {"raw_item": Item, "quantity_per_unit": Decimal (summed)}.
    """
    from collections import defaultdict
    agg: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"quantity_per_unit": Decimal("0"), "raw_item": None})
    for ri in recipe_items:
        raw = ri.raw_item
        key = raw.id
        agg[key]["raw_item"] = raw
        agg[key]["quantity_per_unit"] += Decimal(str(ri.quantity_per_unit))
    return dict(agg)


def production_preview(
    db: Session,
    final_product_id: str,
    quantity: int,
) -> Dict[str, Any]:
    """
    Preview production: required raw items, total quantities, and total cost for N units.
    Same raw item appearing multiple times in the recipe is aggregated (quantities summed).
    Returns dict suitable for ProductionPreviewResponse.
    """
    recipe = get_recipe_by_final_product_id(db, final_product_id)
    if not recipe:
        raise ValueError(f"No recipe found for final product {final_product_id}")

    final = get_item_by_id(db, final_product_id)
    if not final or final.type != ItemType.FINAL_PRODUCT:
        raise ValueError(f"Final product not found or invalid: {final_product_id}")

    aggregated = _aggregate_recipe_by_raw_item(recipe.recipe_items)
    raw_requirements = []
    total_cost = Decimal("0.00")

    for raw_id, data in aggregated.items():
        qty_per_unit = data["quantity_per_unit"]
        raw = data["raw_item"]
        qty_required = qty_per_unit * quantity
        available = raw.total_quantity or 0
        line_cost = (raw.avg_price or Decimal("0.00")) * qty_required
        total_cost += line_cost
        raw_requirements.append({
            "raw_item_id": raw.id,
            "raw_item_name": raw.name,
            "quantity_required": qty_required,
            "quantity_per_unit": qty_per_unit,
            "avg_price": raw.avg_price,
            "available_quantity": available,
            "sufficient": available >= qty_required,
        })

    return {
        "final_product_id": final_product_id,
        "final_product_name": final.name,
        "quantity": quantity,
        "raw_requirements": raw_requirements,
        "total_estimated_cost": total_cost,
    }


def production_feasibility(
    db: Session,
    final_product_id: str,
    quantity: int,
) -> Dict[str, Any]:
    """
    Check if we can produce requested quantity. If not, return max producible and insufficient items.
    Same raw item in multiple recipe lines is aggregated (quantities summed per raw item).
    """
    recipe = get_recipe_by_final_product_id(db, final_product_id)
    if not recipe:
        raise ValueError(f"No recipe found for final product {final_product_id}")

    aggregated = _aggregate_recipe_by_raw_item(recipe.recipe_items)
    max_units = None
    insufficient = []

    for raw_id, data in aggregated.items():
        qty_per_unit = data["quantity_per_unit"]
        raw = data["raw_item"]
        available = raw.total_quantity or 0
        if qty_per_unit <= 0:
            continue
        # Max units this raw item can support (floor)
        max_from_this = int(available / qty_per_unit)
        if max_units is None or max_from_this < max_units:
            max_units = max_from_this

        required_total = qty_per_unit * quantity
        if available < required_total:
            insufficient.append({
                "raw_item_id": raw.id,
                "raw_item_name": raw.name,
                "required_quantity": required_total,
                "available_quantity": available,
                "shortfall": required_total - available,
            })

    if max_units is None:
        max_units = quantity

    feasible = quantity <= max_units and len(insufficient) == 0
    if feasible:
        message = f"You can produce {quantity} unit(s)."
    else:
        message = (
            f"You requested {quantity} unit(s). "
            f"Based on available stock, you can only produce {max_units} unit(s)."
        )

    return {
        "feasible": feasible,
        "requested_quantity": quantity,
        "max_producible_quantity": max_units,
        "insufficient_items": insufficient,
        "message": message,
    }


def production_create_draft(
    db: Session,
    final_product_id: str,
    quantity: int,
    serial_numbers: List[str],
) -> ProductionBatch:
    """
    Create a production batch in DRAFT stage. No inventory is moved.
    Creates a recipe snapshot (batch_recipe_items) that can be modified independently.
    Then production_execute_draft(batch_id) deducts raw items and sets IN_PROCESS.
    Then production_complete_batch(batch_id) adds final product quantity and sets DONE.
    """
    if len(serial_numbers) != quantity:
        raise ValueError(
            f"quantity ({quantity}) must equal number of serial_numbers ({len(serial_numbers)})"
        )

    recipe = get_recipe_by_final_product_id(db, final_product_id)
    if not recipe:
        raise ValueError(f"No recipe found for final product {final_product_id}")

    final = get_item_by_id(db, final_product_id)
    if not final or final.type != ItemType.FINAL_PRODUCT:
        raise ValueError(f"Final product not found or invalid: {final_product_id}")

    existing = (
        db.query(ProductionSerial)
        .filter(ProductionSerial.serial_number.in_(serial_numbers))
        .count()
    )
    if existing > 0:
        raise ValueError("One or more serial numbers are already in use")

    batch_id = _generate_unique_id(db, "PROD", ProductionBatch, length=5)
    batch = ProductionBatch(
        id=batch_id,
        final_product_id=final_product_id,
        quantity_produced=quantity,
        stage=ProductionStage.DRAFT,
    )
    db.add(batch)
    db.flush()

    # Copy master recipe to batch recipe items (snapshot)
    for recipe_item in recipe.recipe_items:
        batch_recipe_item = ProductionBatchRecipeItem(
            production_batch_id=batch.id,
            raw_item_id=recipe_item.raw_item_id,
            quantity_per_unit=recipe_item.quantity_per_unit,
        )
        db.add(batch_recipe_item)

    for sn in serial_numbers:
        ps = ProductionSerial(
            production_batch_id=batch.id,
            serial_number=sn,
            final_product_id=final_product_id,
        )
        db.add(ps)

    try:
        db.commit()
        db.refresh(batch)
        logger.info(f"Production draft created: batch {batch_id}, product {final_product_id}, qty={quantity}")
        return batch
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Production draft create integrity error: {e}")
        raise ValueError("Failed to create production draft (constraint or duplicate serial).")


def production_execute_draft(db: Session, batch_id: str) -> ProductionBatch:
    """
    Execute a DRAFT production batch (Confirm): deduct raw items using batch-specific recipe,
    set stage to IN_PROCESS. User then calls production_complete_batch to mark DONE.
    """
    batch = (
        db.query(ProductionBatch)
        .options(
            joinedload(ProductionBatch.final_product),
            joinedload(ProductionBatch.serials),
            joinedload(ProductionBatch.batch_recipe_items).joinedload(ProductionBatchRecipeItem.raw_item),
        )
        .filter(ProductionBatch.id == batch_id)
        .first()
    )
    if not batch:
        raise ValueError(f"Production batch not found: {batch_id}")
    if batch.stage != ProductionStage.DRAFT:
        raise ValueError(f"Batch {batch_id} is not in DRAFT stage (current: {batch.stage.value})")

    final_product_id = batch.final_product_id
    quantity = batch.quantity_produced
    serial_numbers = [s.serial_number for s in batch.serials]
    if len(serial_numbers) != quantity:
        raise ValueError(
            f"Batch serial count ({len(serial_numbers)}) does not match quantity ({quantity})"
        )

    # Use batch-specific recipe items (not master recipe)
    if not batch.batch_recipe_items:
        raise ValueError(f"Batch {batch_id} has no recipe items")

    final = batch.final_product
    if not final or final.type != ItemType.FINAL_PRODUCT:
        raise ValueError(f"Final product invalid: {final_product_id}")

    # Check feasibility using batch recipe items
    aggregated = _aggregate_recipe_by_raw_item(batch.batch_recipe_items)
    insufficient = []

    for raw_id, data in aggregated.items():
        qty_per_unit = data["quantity_per_unit"]
        raw = data["raw_item"]
        available = raw.total_quantity or 0
        required_total = qty_per_unit * quantity
        if available < required_total:
            insufficient.append({
                "raw_item_name": raw.name,
                "required_quantity": required_total,
                "available_quantity": available,
            })

    if insufficient:
        raise ValueError(
            f"Insufficient stock: "
            + ", ".join(
                f"{x['raw_item_name']} (need {x['required_quantity']}, have {x['available_quantity']})"
                for x in insufficient
            )
        )

    batch.stage = ProductionStage.IN_PROCESS
    db.add(batch)
    db.flush()

    # Deduct raw materials based on batch recipe
    for raw_id, data in aggregated.items():
        qty_per_unit = data["quantity_per_unit"]
        raw = data["raw_item"]
        required_total = qty_per_unit * quantity
        qty_out = _round_required(required_total)
        if qty_out <= 0:
            continue

        raw_row = db.query(Item).filter(Item.id == raw.id).with_for_update().first()
        if not raw_row or raw_row.total_quantity < qty_out:
            db.rollback()
            raise ValueError(
                f"Insufficient stock for {raw.name} ({raw.id}): "
                f"need {qty_out}, have {raw_row.total_quantity if raw_row else 0}"
            )

        raw_row.total_quantity -= qty_out
        stock_id = _generate_unique_id(db, "STK", Stock, length=8)
        stock_entry = Stock(
            id=stock_id,
            item_id=raw.id,
            ref_type=REF_TYPE_PRODUCTION,
            ref_id=batch_id,
            qty_in=0,
            qty_out=qty_out,
            unit_price=raw.avg_price,
        )
        db.add(stock_entry)

    # IN_PROCESS: raw items deducted only. Final product quantity is added when batch is marked DONE.
    try:
        db.commit()
        db.refresh(batch)
        logger.info(
            f"Production draft executed (Confirm): batch {batch_id}, product {final_product_id}, qty={quantity}, stage=IN_PROCESS"
        )
        return batch
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Production execute draft integrity error: {e}")
        raise ValueError("Failed to execute production draft.")


def production_complete_batch(db: Session, batch_id: str) -> ProductionBatch:
    """
    Update batch status from IN_PROCESS to DONE and add final product quantity.
    Raw items were already deducted when batch moved to IN_PROCESS (Confirm).
    """
    batch = (
        db.query(ProductionBatch)
        .options(
            joinedload(ProductionBatch.final_product),
            joinedload(ProductionBatch.serials),
        )
        .filter(ProductionBatch.id == batch_id)
        .first()
    )
    if not batch:
        raise ValueError(f"Production batch not found: {batch_id}")
    if batch.stage != ProductionStage.IN_PROCESS:
        raise ValueError(
            f"Batch {batch_id} is not in IN_PROCESS stage (current: {batch.stage.value}). "
            "Only IN_PROCESS batches can be marked DONE."
        )

    final_product_id = batch.final_product_id
    quantity = batch.quantity_produced
    final = batch.final_product
    if not final:
        final = get_item_by_id(db, final_product_id)
    if not final or final.type != ItemType.FINAL_PRODUCT:
        db.rollback()
        raise ValueError(f"Final product not found or invalid: {final_product_id}")

    # DONE: add final product quantity (raw items were deducted in IN_PROCESS)
    final_row = db.query(Item).filter(Item.id == final_product_id).first()
    if not final_row:
        db.rollback()
        raise ValueError(f"Final product not found: {final_product_id}")
    final_row.total_quantity += quantity
    stock_in_id = _generate_unique_id(db, "STK", Stock, length=8)
    stock_in = Stock(
        id=stock_in_id,
        item_id=final_product_id,
        ref_type=REF_TYPE_PRODUCTION,
        ref_id=batch_id,
        qty_in=quantity,
        qty_out=0,
        unit_price=final.avg_price,
    )
    db.add(stock_in)

    batch.stage = ProductionStage.DONE
    db.add(batch)
    try:
        db.commit()
        db.refresh(batch)
        logger.info(f"Production batch DONE: {batch_id}, added {quantity} to final product {final_product_id}")
        return batch
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Production complete batch error: {e}")
        raise ValueError("Failed to update batch status.")


def _round_required(q: Decimal) -> int:
    """Round required quantity to int for stock ledger (qty_in/qty_out are int)."""
    return int(q.to_integral_value(rounding=ROUND_HALF_UP))


def get_production_batch(db: Session, batch_id: str) -> Optional[ProductionBatch]:
    """Get a production batch by ID with relationships loaded."""
    return (
        db.query(ProductionBatch)
        .options(
            joinedload(ProductionBatch.final_product),
            joinedload(ProductionBatch.serials),
            joinedload(ProductionBatch.batch_recipe_items).joinedload(ProductionBatchRecipeItem.raw_item),
        )
        .filter(ProductionBatch.id == batch_id)
        .first()
    )


def list_production_batches(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    final_product_id: Optional[str] = None,
    stage: Optional[ProductionStage] = None,
) -> tuple[List[ProductionBatch], int]:
    """List production batches with optional filters. Returns (items, total_count)."""
    query = db.query(ProductionBatch).options(
        joinedload(ProductionBatch.final_product),
        joinedload(ProductionBatch.serials),
    )
    if final_product_id:
        query = query.filter(ProductionBatch.final_product_id == final_product_id)
    if stage is not None:
        query = query.filter(ProductionBatch.stage == stage)
    total = query.count()
    batches = query.order_by(ProductionBatch.created_at.desc()).offset(skip).limit(limit).all()
    return batches, total


def get_production_batch_detail(db: Session, batch_id: str) -> Dict[str, Any]:
    """
    Get detailed production batch info including recipe items and cost calculations.
    Returns dict suitable for ProductionBatchDetailResponse.
    """
    batch = get_production_batch(db, batch_id)
    if not batch:
        raise ValueError(f"Production batch not found: {batch_id}")

    serial_numbers = [s.serial_number for s in batch.serials] if batch.serials else []
    
    # Calculate costs based on batch recipe items
    recipe_items_response = []
    total_cost = Decimal("0.00")
    
    for batch_item in batch.batch_recipe_items:
        raw = batch_item.raw_item
        qty_per_unit = Decimal(str(batch_item.quantity_per_unit))
        avg_price = raw.avg_price or Decimal("0.00")
        line_cost = qty_per_unit * avg_price * batch.quantity_produced
        total_cost += line_cost
        
        recipe_items_response.append({
            "id": batch_item.id,
            "raw_item_id": raw.id,
            "raw_item_name": raw.name,
            "quantity_per_unit": qty_per_unit,
            "avg_price": avg_price,
            "total_quantity": raw.total_quantity,
        })
    
    cost_per_unit = total_cost / batch.quantity_produced if batch.quantity_produced > 0 else Decimal("0.00")
    
    return {
        "id": batch.id,
        "final_product_id": batch.final_product_id,
        "final_product_name": batch.final_product.name if batch.final_product else "—",
        "quantity_produced": batch.quantity_produced,
        "stage": batch.stage.value if hasattr(batch.stage, "value") else batch.stage,
        "serial_numbers": serial_numbers,
        "recipe_items": recipe_items_response,
        "total_estimated_cost": total_cost,
        "cost_per_unit": cost_per_unit,
        "created_at": batch.created_at,
        "updated_at": batch.updated_at,
    }


def update_production_batch(
    db: Session,
    batch_id: str,
    quantity: Optional[int] = None,
    serial_numbers: Optional[List[str]] = None,
    recipe_items: Optional[List[Dict[str, Any]]] = None,
) -> ProductionBatch:
    """
    Update a production batch in DRAFT stage.
    Can update quantity, serial numbers, and/or recipe items (batch-specific).
    Changes to recipe items do NOT affect the master recipe.
    """
    batch = get_production_batch(db, batch_id)
    if not batch:
        raise ValueError(f"Production batch not found: {batch_id}")
    
    if batch.stage != ProductionStage.DRAFT:
        raise ValueError(
            f"Batch {batch_id} is not in DRAFT stage (current: {batch.stage.value}). "
            "Only DRAFT batches can be updated."
        )
    
    # Update quantity
    if quantity is not None:
        batch.quantity_produced = quantity
    
    # Update serial numbers
    if serial_numbers is not None:
        if len(serial_numbers) != batch.quantity_produced:
            raise ValueError(
                f"Number of serial numbers ({len(serial_numbers)}) must match quantity ({batch.quantity_produced})"
            )
        
        # Check for duplicates with existing serials (excluding this batch)
        existing = (
            db.query(ProductionSerial)
            .filter(
                ProductionSerial.serial_number.in_(serial_numbers),
                ProductionSerial.production_batch_id != batch_id,
            )
            .count()
        )
        if existing > 0:
            raise ValueError("One or more serial numbers are already in use by another batch")
        
        # Delete existing serials and create new ones
        db.query(ProductionSerial).filter(ProductionSerial.production_batch_id == batch_id).delete()
        for sn in serial_numbers:
            ps = ProductionSerial(
                production_batch_id=batch.id,
                serial_number=sn,
                final_product_id=batch.final_product_id,
            )
            db.add(ps)
    
    # Update recipe items (batch-specific, does not affect master recipe)
    if recipe_items is not None:
        if not recipe_items:
            raise ValueError("At least one recipe item is required")
        
        # Validate all raw items exist
        raw_item_ids = [item["raw_item_id"] for item in recipe_items]
        existing_items = db.query(Item).filter(Item.id.in_(raw_item_ids)).all()
        existing_ids = {item.id for item in existing_items}
        
        for item_id in raw_item_ids:
            if item_id not in existing_ids:
                raise ValueError(f"Raw item not found: {item_id}")
            item_obj = next(i for i in existing_items if i.id == item_id)
            if item_obj.type != ItemType.RAW_MATERIAL:
                raise ValueError(f"Item {item_id} is not a raw material")
        
        # Delete existing batch recipe items and create new ones
        db.query(ProductionBatchRecipeItem).filter(
            ProductionBatchRecipeItem.production_batch_id == batch_id
        ).delete()
        
        for item in recipe_items:
            batch_recipe_item = ProductionBatchRecipeItem(
                production_batch_id=batch.id,
                raw_item_id=item["raw_item_id"],
                quantity_per_unit=Decimal(str(item["quantity_per_unit"])),
            )
            db.add(batch_recipe_item)
    
    try:
        db.commit()
        db.refresh(batch)
        logger.info(f"Production batch updated: {batch_id}")
        return batch
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Production batch update integrity error: {e}")
        raise ValueError("Failed to update production batch.")


def delete_production_batch(db: Session, batch_id: str) -> None:
    """
    Delete a production batch. Only DRAFT batches can be deleted.
    IN_PROCESS and DONE batches cannot be deleted as they have already affected inventory.
    Deletes batch along with serials and recipe items (CASCADE).
    """
    batch = get_production_batch(db, batch_id)
    if not batch:
        raise ValueError(f"Production batch not found: {batch_id}")
    
    # if batch.stage != ProductionStage.DRAFT:
    #     raise ValueError(
    #         f"Cannot delete batch {batch_id} in {batch.stage.value} stage. "
    #         "Only DRAFT batches can be deleted."
    #     )
    
    try:
        db.delete(batch)
        db.commit()
        logger.info(f"Production batch deleted: {batch_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete production batch {batch_id}: {e}")
        raise ValueError(f"Failed to delete production batch: {str(e)}")
