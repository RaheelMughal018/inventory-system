from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)


class CustomerCreate(CustomerBase):
    opening_balance: Optional[Decimal] = Field(default=Decimal('0.00'), ge=0, description="Opening balance amount")
    opening_balance_type: Optional[Literal['DEBIT', 'CREDIT']] = Field(
        default='DEBIT',
        description="DEBIT = Customer owes you, CREDIT = You owe customer"
    )

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)
    opening_balance: Optional[Decimal] = Field(None, ge=0, description="Opening balance amount")
    opening_balance_type: Optional[Literal['DEBIT', 'CREDIT']] = Field(
        None,
        description="DEBIT = Customer owes you, CREDIT = You owe customer"
    )


class CustomerResponse(CustomerBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None
    opening_balance: Optional[Decimal] = Decimal('0.00')
    opening_balance_type: Optional[str] = 'DEBIT'
    # total_transactions: Optional[Decimal] = None
    # total_paid: Optional[Decimal] = None
    # current_balance: Optional[Decimal] = None

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    total: int
    customers: list[CustomerResponse]


class CustomerDeleteResponse(BaseModel):
    message: str