from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.models.user import UserRole

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict  # User information

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)
    name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.owner  # Default to owner for first user
