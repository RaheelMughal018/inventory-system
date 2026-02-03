from decimal import Decimal
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class StockLedgerItemRef(BaseModel):
    """Minimal item reference for stock ledger list."""
    id: str
    name: str

    class Config:
        from_attributes = True


class StockLedgerBase(BaseModel):
    id: str
    item_id: str
    ref_type: Optional[str] = None
    ref_id: Optional[str] = None
    qty_in: int = 0
    qty_out: int = 0
    unit_price: Optional[Decimal] = None
    created_at: datetime
    item: StockLedgerItemRef

    class Config:
        from_attributes = True


class StockLedgerResponse(BaseModel):
    data: List[StockLedgerBase]
    count: int
    total_dic: dict
