from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from app.models.payment import PaymentAccountType


class AccountCreate(BaseModel):
    name: str
    type: PaymentAccountType
    opening_balance: Optional[Decimal] = Field(default=Decimal("0"), ge=0, description="Opening balance (money in account)")


class UpdateAccount(BaseModel):
    name: Optional[str] = None
    type: Optional[PaymentAccountType] = None
    opening_balance: Optional[Decimal] = Field(None, ge=0)


class AccountResponse(BaseModel):
    id: str
    name: str
    type: PaymentAccountType
    opening_balance: Optional[Decimal] = Decimal("0")
    created_at: datetime

    class Config:
        from_attributes = True


class AccountBalanceResponse(BaseModel):
    account_id: str
    account_name: str
    balance: Decimal
    opening_balance: Decimal


class AccountDeleteResponse(BaseModel):
    message: str


class AccountListResponse(BaseModel):
    total: int
    accounts: List[AccountResponse]
