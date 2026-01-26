from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum


class ItemType(str, Enum):
    final_product = "final_product"
    raw_material = "raw_material"


class UnitType(str, Enum):
    PCS = "PCS"
    SET = "SET"


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category_id: str
    type: ItemType
    unit_type: UnitType
    avg_price: Optional[Decimal] = Field(0, ge=0)

# class ItemUpdate(BaseModel):
#     name: Optional[str] = Field(None, min_length=1, max_length=100)
#     category_id: Optional[str] = None
#     type: Optional[ItemType] = None
#     unit_type: Optional[UnitType] = None
#     avg_price: Optional[Decimal] = Field(None, ge=0)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(ItemBase):
    pass


class ItemResponse(ItemBase):
    id: str
    avg_price: Decimal
    total_quantity: int
    created_at: datetime

    class Config:
        from_attributes = True


class ItemListResponse(BaseModel):
    total: int
    items: list[ItemResponse]


class ItemDeleteResponse(BaseModel):
    message: str
