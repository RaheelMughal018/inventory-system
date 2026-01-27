from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.models.item_category import ItemType
from app.services.item_service import (
    get_item_by_id,
    get_item_by_name,
    get_all_items,
    create_item,
    update_item,
    delete_item
)
from app.schemas.item import (
    ItemCreate,
    ItemUpdate,
    ItemResponse,
    ItemListResponse,
    ItemDeleteResponse
)
from app.logger_config import logger

router = APIRouter()


@router.get("", response_model=ItemListResponse)
def get_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    item_type: Optional[ItemType] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all items with optional filtering.
    Requires authentication.
    """
    try:
        items, total = get_all_items(
            db, 
            skip=skip, 
            limit=limit, 
            search=search,
            category_id=category_id,
            item_type=item_type
        )
        
        return ItemListResponse(
            total=total,
            items=[ItemResponse.model_validate(item) for item in items]
        )
    except Exception as e:
        logger.error(f"Error fetching items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch items"
        )


@router.get("/name/{item_name}", response_model=ItemResponse)
def get_item_by_name_route(
    item_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get item by name.
    Requires authentication.
    """
    item = get_item_by_name(db, item_name)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return ItemResponse.model_validate(item)


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(
    item_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get item by ID.
    Requires authentication.
    """
    item = get_item_by_id(db, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return ItemResponse.model_validate(item)


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item_route(
    item_data: ItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new item.
    Requires authentication.
    """
    try:
        item = create_item(
            db=db,
            name=item_data.name,
            type=item_data.type,
            unit_type=item_data.unit_type,
            category_id=item_data.category_id,
        )
        
        logger.info(f"Item {item.name} created by {current_user.email}")
        
        return ItemResponse.model_validate(item)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create item"
        )


@router.put("/{item_id}", response_model=ItemResponse)
def update_item_route(
    item_id: str,
    item_data: ItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update item information.
    Requires authentication.
    """
    try:
        item = update_item(
            db=db,
            item_id=item_id,
            name=item_data.name,
            type=item_data.type,
            unit_type=item_data.unit_type,
            category_id=item_data.category_id,
        )
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        logger.info(f"Item {item_id} updated by {current_user.email}")
        
        return ItemResponse.model_validate(item)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update item"
        )


@router.delete("/{item_id}", response_model=ItemDeleteResponse)
def delete_item_route(
    item_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an item.
    Requires authentication.
    Only owners can delete items.
    """
    from app.models.user import UserRole
    
    if current_user.role != UserRole.owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can delete items"
        )
    
    try:
        success = delete_item(db, item_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        logger.info(f"Item {item_id} deleted by {current_user.email}")
        
        return ItemDeleteResponse(
            message="Item deleted successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete item"
        )
