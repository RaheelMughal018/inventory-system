from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.schemas.expense_category import (
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
    ExpenseCategoryResponse,
    ExpenseCategoryListResponse,
    ExpenseCategoryDeleteResponse,
)
from app.services.expense_category_service import (
    get_expense_category_by_id,
    get_all_expense_categories,
    create_expense_category,
    update_expense_category,
    delete_expense_category,
)
from app.logger_config import logger

router = APIRouter()


@router.get("", response_model=ExpenseCategoryListResponse)
def list_expense_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all expense categories (bike repair, bills, bilty, etc.) with optional search."""
    try:
        categories, total = get_all_expense_categories(db, skip=skip, limit=limit, search=search)
        return ExpenseCategoryListResponse(
            total=total,
            categories=[ExpenseCategoryResponse.model_validate(c) for c in categories],
        )
    except Exception as e:
        logger.error(f"Error fetching expense categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch expense categories",
        )


@router.get("/{category_id}", response_model=ExpenseCategoryResponse)
def get_expense_category(
    category_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get expense category by ID."""
    category = get_expense_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense category not found")
    return ExpenseCategoryResponse.model_validate(category)


@router.post("", response_model=ExpenseCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_expense_category_route(
    data: ExpenseCategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new expense category (e.g. bike repair, bills, loan)."""
    try:
        category = create_expense_category(db, name=data.name)
        logger.info(f"Expense category {category.name} created by {current_user.name}")
        return ExpenseCategoryResponse.model_validate(category)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating expense category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create expense category",
        )


@router.put("/{category_id}", response_model=ExpenseCategoryResponse)
def update_expense_category_route(
    category_id: str,
    data: ExpenseCategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update expense category."""
    try:
        category = update_expense_category(db, category_id=category_id, name=data.name)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense category not found")
        return ExpenseCategoryResponse.model_validate(category)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating expense category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update expense category",
        )


@router.delete("/{category_id}", response_model=ExpenseCategoryDeleteResponse)
def delete_expense_category_route(
    category_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete expense category (only if it has no expenses)."""
    try:
        success = delete_expense_category(db, category_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense category not found")
        return ExpenseCategoryDeleteResponse(message="Expense category deleted successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting expense category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete expense category",
        )
