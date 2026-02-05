"""
Recipe API: CRUD for recipes (final product -> raw items with quantities).
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.schemas.recipe import (
    RecipeCreate,
    RecipeUpdate,
    RecipeResponse,
    RecipeListResponse,
    RecipeItemResponse,
)
from app.services.recipe_service import (
    create_recipe,
    get_recipe_by_id,
    get_recipe_by_final_product_id,
    get_all_recipes,
    update_recipe,
    delete_recipe,
)
from app.logger_config import logger

router = APIRouter()


def _two_decimal(d):
    """Round to 2 decimal places for API response."""
    from decimal import Decimal, ROUND_HALF_UP
    if d is None:
        return None
    v = Decimal(str(d))
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _build_recipe_response(recipe) -> RecipeResponse:
    """Build RecipeResponse from ORM recipe. amount_per_unit = quantity_per_unit × avg_price (e.g. 4 wheels × 90 = 360)."""
    from decimal import Decimal
    total_cost_per_unit = Decimal("0.00")
    items = []
    for ri in recipe.recipe_items:
        raw = ri.raw_item
        qty = _two_decimal(ri.quantity_per_unit)
        avg = raw.avg_price if raw and raw.avg_price is not None else Decimal("0.00")
        amount_per_unit = _two_decimal(Decimal(str(ri.quantity_per_unit)) * avg)
        total_cost_per_unit += Decimal(str(ri.quantity_per_unit)) * avg
        items.append(
            RecipeItemResponse(
                id=ri.id,
                raw_item_id=ri.raw_item_id,
                raw_item_name=raw.name if raw else "—",
                quantity_per_unit=qty,
                avg_price=_two_decimal(raw.avg_price) if raw else None,
                amount_per_unit=amount_per_unit,
                total_quantity=raw.total_quantity if raw else 0,
            )
        )
    return RecipeResponse(
        id=recipe.id,
        final_product_id=recipe.final_product_id,
        final_product_name=recipe.final_product.name if recipe.final_product else "—",
        name=recipe.name,
        items=items,
        total_cost_per_unit=_two_decimal(total_cost_per_unit),
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
    )


@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def create_recipe_route(
    data: RecipeCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a recipe for a final product. One recipe per final product."""
    try:
        items = [{"raw_item_id": x.raw_item_id, "quantity_per_unit": x.quantity_per_unit} for x in data.items]
        recipe = create_recipe(
            db,
            final_product_id=data.final_product_id,
            items=items,
            name=data.name,
        )
        return _build_recipe_response(recipe)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error creating recipe")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create recipe",
        )


@router.get("", response_model=RecipeListResponse)
def list_recipes(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
):
    """List all recipes with optional search by final product name/id."""
    try:
        recipes, total = get_all_recipes(db, skip=skip, limit=limit, search=search)
        return RecipeListResponse(
            total=total,
            recipes=[_build_recipe_response(r) for r in recipes],
        )
    except Exception as e:
        logger.exception("Error listing recipes")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list recipes",
        )


@router.get("/product/{final_product_id}", response_model=RecipeResponse)
def get_recipe_by_product_route(
    final_product_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get recipe by final product ID."""
    recipe = get_recipe_by_final_product_id(db, final_product_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recipe found for final product {final_product_id}",
        )
    return _build_recipe_response(recipe)


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe_route(
    recipe_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get recipe by ID."""
    recipe = get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe not found: {recipe_id}",
        )
    return _build_recipe_response(recipe)


@router.put("/{recipe_id}", response_model=RecipeResponse)
def update_recipe_route(
    recipe_id: str,
    data: RecipeUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update recipe name and/or replace recipe items."""
    try:
        items_data = None
        if data.items is not None:
            items_data = [{"raw_item_id": x.raw_item_id, "quantity_per_unit": x.quantity_per_unit} for x in data.items]
        recipe = update_recipe(db, recipe_id=recipe_id, name=data.name, items=items_data)
        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recipe not found: {recipe_id}",
            )
        return _build_recipe_response(recipe)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error updating recipe")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update recipe",
        )


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe_route(
    recipe_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a recipe (does not delete the final product or raw items)."""
    try:
        deleted = delete_recipe(db, recipe_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recipe not found: {recipe_id}",
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
