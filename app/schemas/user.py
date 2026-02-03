from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr | None
    name: str = Field(..., min_length=1, max_length=255)
    role: UserRole

    model_config = ConfigDict(from_attributes=True)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)
    created_by_id: Optional[int] = None


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None


class UserResponse(UserBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None

    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Extended user response with profile information."""
    profile_picture: Optional[str] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    total: int
    users: list[UserResponse]


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=100)
