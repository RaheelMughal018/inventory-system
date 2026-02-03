from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseCreateBulk,
    ExpenseResponse,
    ExpenseListResponse,
    ExpenseTotalTodayResponse,
)
from app.services.expense_service import (
    create_expense,
    create_expenses_bulk,
    get_all_expenses,
    get_total_expense_today,
)
from app.logger_config import logger

router = APIRouter()


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_single_expense(
    data: ExpenseCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a single expense; date defaults to today if not provided. Creates a financial ledger entry."""
    try:
        expense = create_expense(
            db,
            amount=data.amount,
            name=data.name,
            account_id=data.account_id,
            expense_category_id=data.expense_category_id,
            description=data.description,
            user_id=data.user_id,
            expense_date=data.date,
            ledger_user_id=current_user.id,
        )
        return ExpenseResponse.model_validate(expense)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error creating expense")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create expense",
        )


@router.post("/bulk", response_model=ExpenseListResponse, status_code=status.HTTP_201_CREATED)
def create_bulk_expenses(
    data: ExpenseCreateBulk,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add multiple expenses for a day (e.g. current day). Date defaults to today."""
    try:
        items = [
            {
                "amount": e.amount,
                "name": e.name,
                "account_id": e.account_id,
                "expense_category_id": e.expense_category_id,
                "description": e.description,
                "user_id": e.user_id,
            }
            for e in data.expenses
        ]
        created = create_expenses_bulk(
            db, items=items, expense_date=data.date, ledger_user_id=current_user.id
        )
        total_amount = sum(exp.amount for exp in created)
        return ExpenseListResponse(
            total=len(created),
            total_amount=total_amount,
            expenses=[ExpenseResponse.model_validate(exp) for exp in created],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error creating bulk expenses")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create expenses",
        )


@router.get("", response_model=ExpenseListResponse)
def list_expenses(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    expense_category_id: Optional[str] = Query(None),
    expense_date: Optional[date] = Query(None, description="Filter by specific day"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_active_user),
):
    """List expenses with filters: user, category, day or date range."""
    try:
        rows, total_count, total_amount = get_all_expenses(
            db,
            skip=skip,
            limit=limit,
            user_id=user_id,
            expense_category_id=expense_category_id,
            expense_date=expense_date,
            start_date=start_date,
            end_date=end_date,
        )
        return ExpenseListResponse(
            total=total_count,
            total_amount=total_amount,
            expenses=[ExpenseResponse.model_validate(r) for r in rows],
        )
    except Exception as e:
        logger.exception("Error fetching expenses")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch expenses",
        )


@router.get("/total-today", response_model=ExpenseTotalTodayResponse)
def get_total_expense_today_route(
    db: Session = Depends(get_db),
    user_id: Optional[int] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_active_user),
):
    """Get total expense amount for today; optional filter by user."""
    try:
        today, total_amount, count = get_total_expense_today(db, user_id=user_id)
        return ExpenseTotalTodayResponse(
            date=today,
            total_amount=total_amount,
            count=count,
        )
    except Exception as e:
        logger.exception("Error fetching today's expense total")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch today's expense total",
        )
