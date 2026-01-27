from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.item_category import ItemType, UnitType
from app.schemas.category import CategoryResponse


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: ItemType
    unit_type: UnitType
    category_id: str = Field(..., min_length=1, max_length=20)


class ItemCreate(ItemBase):
    avg_price: Optional[Decimal] = None
    total_quantity: Optional[int] = None

class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[ItemType] = None
    unit_type: Optional[UnitType] = None
    category_id: Optional[str] = Field(None, min_length=1, max_length=20)
   


class ItemResponse(ItemBase):
    id: str
    avg_price: Optional[Decimal] = None
    total_quantity: int
    category: CategoryResponse
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ItemListResponse(BaseModel):
    total: int
    items: list[ItemResponse]


class ItemDeleteResponse(BaseModel):
    message: str
