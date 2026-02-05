"""
Production API: preview, feasibility check, and execution.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path

from app.core.dependencies import get_db, get_current_active_user
from app.models.recipe import ProductionStage
from app.models.user import User
from app.schemas.recipe import (
    ProductionFeasibilityRequest,
    ProductionFeasibilityResponse,
    ProductionPreviewResponse,
    ProductionDraftCreate,
    ProductionBatchResponse,
    ProductionBatchDetailResponse,
    ProductionBatchUpdate,
    ProductionBatchListResponse,
    ProductionStageEnum,
    RawItemRequirement,
    InsufficientItem,
)
from app.services.production_service import (
    production_preview,
    production_feasibility,
    production_create_draft,
    production_execute_draft,
    production_complete_batch,
    get_production_batch,
    get_production_batch_detail,
    update_production_batch,
    delete_production_batch,
    list_production_batches,
)
from app.logger_config import logger
from sqlalchemy.orm import Session
from typing import Optional

router = APIRouter()


def _batch_stage_enum(value) -> ProductionStageEnum:
    """Map DB stage string to schema enum."""
    return ProductionStageEnum(value) if value else ProductionStageEnum.DRAFT


def _build_batch_response(batch) -> ProductionBatchResponse:
    serials = [s.serial_number for s in batch.serials] if batch.serials else []
    return ProductionBatchResponse(
        id=batch.id,
        final_product_id=batch.final_product_id,
        final_product_name=batch.final_product.name if batch.final_product else "—",
        quantity_produced=batch.quantity_produced,
        stage=_batch_stage_enum(batch.stage.value if hasattr(batch.stage, "value") else batch.stage),
        serial_numbers=serials,
        created_at=batch.created_at,
        updated_at=getattr(batch, "updated_at", None),
    )


@router.get("/preview", response_model=ProductionPreviewResponse)
def production_preview_route(
    final_product_id: str = Query(..., description="Final product item ID"),
    quantity: int = Query(1, ge=1, description="Number of units to produce"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Production preview: for the given final product and quantity, show required raw items,
    total quantity per item, and total estimated cost (based on average price).
    """
    try:
        data = production_preview(db, final_product_id=final_product_id, quantity=quantity)
        raw_requirements = [
            RawItemRequirement(
                raw_item_id=r["raw_item_id"],
                raw_item_name=r["raw_item_name"],
                quantity_required=r["quantity_required"],
                quantity_per_unit=r["quantity_per_unit"],
                avg_price=r.get("avg_price"),
                available_quantity=r["available_quantity"],
                sufficient=r["sufficient"],
            )
            for r in data["raw_requirements"]
        ]
        return ProductionPreviewResponse(
            final_product_id=data["final_product_id"],
            final_product_name=data["final_product_name"],
            quantity=data["quantity"],
            raw_requirements=raw_requirements,
            total_estimated_cost=data["total_estimated_cost"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error in production preview")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get production preview",
        )


@router.post("/feasibility", response_model=ProductionFeasibilityResponse)
def production_feasibility_route(
    data: ProductionFeasibilityRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Check if requested quantity can be produced with current stock.
    If not, returns max producible quantity and which raw items are insufficient.
    """
    try:
        result = production_feasibility(
            db,
            final_product_id=data.final_product_id,
            quantity=data.quantity,
        )
        insufficient = [
            InsufficientItem(
                raw_item_id=x["raw_item_id"],
                raw_item_name=x["raw_item_name"],
                required_quantity=x["required_quantity"],
                available_quantity=x["available_quantity"],
                shortfall=x["shortfall"],
            )
            for x in result["insufficient_items"]
        ]
        return ProductionFeasibilityResponse(
            feasible=result["feasible"],
            requested_quantity=result["requested_quantity"],
            max_producible_quantity=result["max_producible_quantity"],
            insufficient_items=insufficient,
            message=result["message"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error in production feasibility")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check feasibility",
        )


@router.post("/draft", response_model=ProductionBatchResponse, status_code=status.HTTP_201_CREATED)
def production_create_draft_route(
    data: ProductionDraftCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Start production: create a batch in DRAFT stage. No inventory is moved.
    Then: Confirm = POST /batches/{batch_id}/execute (deduct raw items only, stage → IN_PROCESS).
    Then: POST /batches/{batch_id}/complete (add final product quantity, stage → DONE).
    """
    try:
        batch = production_create_draft(
            db,
            final_product_id=data.final_product_id,
            quantity=data.quantity,
            serial_numbers=data.serial_numbers,
        )
        return _build_batch_response(batch)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error creating production draft")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create production draft",
        )


@router.post("/batches/{batch_id}/execute", response_model=ProductionBatchResponse)
def production_execute_draft_route(
    batch_id: str = Path(..., description="DRAFT batch ID to execute (Confirm button)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Confirm production: deduct raw items only, set stage to IN_PROCESS.
    Call POST /batches/{batch_id}/complete to add final product quantity and set DONE.
    """
    try:
        batch = production_execute_draft(db, batch_id=batch_id)
        return _build_batch_response(batch)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error executing production draft")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute production draft",
        )


@router.post("/batches/{batch_id}/complete", response_model=ProductionBatchResponse)
def production_complete_batch_route(
    batch_id: str = Path(..., description="IN_PROCESS batch ID to mark as DONE"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Mark batch as DONE: add final product quantity to inventory and set status to DONE.
    Raw items were already deducted when batch was set to IN_PROCESS (Confirm).
    """
    try:
        batch = production_complete_batch(db, batch_id=batch_id)
        return _build_batch_response(batch)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error completing production batch")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete production batch",
        )


@router.get("/batches", response_model=ProductionBatchListResponse)
def list_production_batches_route(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    final_product_id: Optional[str] = Query(None),
    stage: Optional[ProductionStageEnum] = Query(None),
    current_user: User = Depends(get_current_active_user),
):
    """
    List production batches with optional filters: final_product_id, stage (DRAFT, IN_PROCESS, DONE).
    """
    try:
        stage_filter = ProductionStage(stage.value) if stage is not None else None
        batches, total = list_production_batches(
            db,
            skip=skip,
            limit=limit,
            final_product_id=final_product_id,
            stage=stage_filter,
        )
        return ProductionBatchListResponse(
            total=total,
            batches=[_build_batch_response(b) for b in batches],
        )
    except Exception as e:
        logger.exception("Error listing production batches")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list production batches",
        )


@router.get("/batches/{batch_id}", response_model=ProductionBatchResponse)
def get_production_batch_route(
    batch_id: str = Path(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a single production batch by ID (basic info)."""
    batch = get_production_batch(db, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production batch not found: {batch_id}",
        )
    return _build_batch_response(batch)


@router.get("/batches/{batch_id}/detail", response_model=ProductionBatchDetailResponse)
def get_production_batch_detail_route(
    batch_id: str = Path(..., description="Production batch ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed production batch info including recipe snapshot, cost calculations.
    Useful for viewing/editing a DRAFT batch before execution.
    """
    try:
        detail = get_production_batch_detail(db, batch_id)
        return ProductionBatchDetailResponse(**detail)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception("Error getting production batch detail")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get production batch detail",
        )


@router.patch("/batches/{batch_id}", response_model=ProductionBatchDetailResponse)
def update_production_batch_route(
    batch_id: str = Path(..., description="DRAFT batch ID to update"),
    data: ProductionBatchUpdate = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update a DRAFT production batch: modify quantity, serial numbers, and/or recipe items.
    Recipe changes apply only to this batch and do NOT affect the master recipe.
    Only DRAFT batches can be updated.
    """
    try:
        recipe_items_dict = None
        if data.recipe_items:
            recipe_items_dict = [
                {
                    "raw_item_id": item.raw_item_id,
                    "quantity_per_unit": item.quantity_per_unit,
                }
                for item in data.recipe_items
            ]
        
        batch = update_production_batch(
            db,
            batch_id=batch_id,
            quantity=data.quantity,
            serial_numbers=data.serial_numbers,
            recipe_items=recipe_items_dict,
        )
        
        # Return detailed response with updated calculations
        detail = get_production_batch_detail(db, batch_id)
        return ProductionBatchDetailResponse(**detail)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error updating production batch")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update production batch",
        )


@router.delete("/batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_production_batch_route(
    batch_id: str = Path(..., description="DRAFT batch ID to delete"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a DRAFT production batch.
    Only DRAFT batches can be deleted. IN_PROCESS and DONE batches cannot be deleted
    as they have already affected inventory.
    Deletes batch along with all serial numbers and recipe items.
    """
    try:
        delete_production_batch(db, batch_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error deleting production batch")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete production batch",
        )
