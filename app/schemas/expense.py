from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime

# Alias to avoid field name 'date' shadowing type 'date' in annotations (Pydantic v2)
DateType = date


class ExpenseCreate(BaseModel):
    """Single expense create - date defaults to today on server if not provided."""
    date: Optional[DateType] = None  # default to today in service
    name: str = Field(..., min_length=1, max_length=100)
    amount: Decimal = Field(..., gt=0)
    account_id: str = Field(..., min_length=1)
    expense_category_id: str = Field(..., min_length=1)
    description: Optional[str] = None
    user_id: Optional[int] = None


class ExpenseCreateBulk(BaseModel):
    """Add multiple expenses for a day (e.g. current day)."""
    date: Optional[DateType] = None  # default to today
    expenses: List[ExpenseCreate] = Field(..., min_length=1)


# Refs for nested response (avoid circular imports)
class ExpenseAccountRef(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


class ExpenseCategoryRef(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


class ExpenseUserRef(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ExpenseResponse(BaseModel):
    id: str
    date: DateType
    amount: Decimal
    account_id: str
    name: str
    expense_category_id: str
    description: Optional[str] = None
    user_id: Optional[int] = None
    created_at: datetime
    account: ExpenseAccountRef
    category: ExpenseCategoryRef
    user: Optional[ExpenseUserRef] = None

    class Config:
        from_attributes = True


class ExpenseListResponse(BaseModel):
    total: int
    total_amount: Decimal
    expenses: List[ExpenseResponse]


class ExpenseTotalTodayResponse(BaseModel):
    """Total expense amount for today."""
    date: DateType
    total_amount: Decimal
    count: int
