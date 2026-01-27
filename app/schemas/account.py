from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.payment import PaymentAccountType


class AccountCreate(BaseModel):
    name: str
    type: PaymentAccountType


class UpdateAccount(BaseModel):
    name: Optional[str] = None
    type: Optional[PaymentAccountType] = None


class AccountResponse(BaseModel):
    id: str
    name: str
    type: PaymentAccountType
    created_at: datetime

    class Config:
        from_attributes = True


class AccountDeleteResponse(BaseModel):
    message: str


class AccountListResponse(BaseModel):
    total: int
    accounts: List[AccountResponse]
