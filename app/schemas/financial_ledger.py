from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.schemas.user import UserBase



class FinancialLedgerBase(BaseModel):
    id: int
    user_id: int
    ref_type: str
    ref_id: str
    debit: Decimal
    credit: Decimal
    created_at: datetime
    user: UserBase

    class Config:
        from_attributes = True


class FinancialLedgerResponse(BaseModel):
    data: List[FinancialLedgerBase]
    count: int
    total_dic: dict
