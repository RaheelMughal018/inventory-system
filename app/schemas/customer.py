from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)


class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)


class CustomerResponse(CustomerBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None
    total_transactions: Optional[Decimal] = None
    total_paid: Optional[Decimal] = None
    current_balance: Optional[Decimal] = None

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    total: int
    customers: list[CustomerResponse]


class CustomerDeleteResponse(BaseModel):
    message: str