from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ExpenseCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class ExpenseCategoryCreate(ExpenseCategoryBase):
    pass


class ExpenseCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)


class ExpenseCategoryResponse(ExpenseCategoryBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class ExpenseCategoryListResponse(BaseModel):
    total: int
    categories: list[ExpenseCategoryResponse]


class ExpenseCategoryDeleteResponse(BaseModel):
    message: str
