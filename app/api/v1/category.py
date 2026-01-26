from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.services.category_service import (
    get_category_by_id,
    get_all_categories,
    create_category,
    update_category,
    delete_category
)
from app.schemas.category import (
    CategoryCreate,
    CategoryDeleteResponse,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse
)
from app.logger_config import logger

router = APIRouter()


@router.get("", response_model=CategoryListResponse)
def get_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all categories with optional search filtering.
    Requires authentication.
    """
    try:
        categories, total = get_all_categories(
            db, skip=skip, limit=limit, search=search)

        category_responses = [
            CategoryResponse(
                id=category.id,
                name=category.name,
                created_at=category.created_at
            )
            for category in categories
        ]

        return CategoryListResponse(
            total=total,
            categories=category_responses
        )
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch categories"
        )


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get category by ID.
    Requires authentication.
    """
    category = get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    return CategoryResponse(
        id=category.id,
        name=category.name,
        created_at=category.created_at
    )


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_new_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new category.
    Requires authentication.
    """
    try:
        category = create_category(db, name=category_data.name)

        return CategoryResponse(
            id=category.id,
            name=category.name,
            created_at=category.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category"
        )


@router.put("/{category_id}", response_model=CategoryResponse)
def update_existing_category(
    category_id: str,
    category_data: CategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing category.
    Requires authentication.
    """
    try:
        category = update_category(
            db,
            category_id=category_id,
            name=category_data.name
        )

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

        return CategoryResponse(
            id=category.id,
            name=category.name,
            created_at=category.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category"
        )


@router.delete("/{category_id}", response_model=CategoryDeleteResponse)
def delete_existing_category(
    category_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a category.
    Requires authentication.
    """
    try:
        success = delete_category(db, category_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

        return CategoryDeleteResponse(
            message=f"Category {category_id} deleted successfully"
        )
    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category"
        )
