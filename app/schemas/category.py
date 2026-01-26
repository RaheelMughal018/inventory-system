from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    total: int
    categories: list[CategoryResponse]


class CategoryDeleteResponse(BaseModel):
    message: str
