from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import decode_access_token



def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Use HTTPBearer so Swagger automatically asks for a token
bearer_scheme = HTTPBearer(auto_error=True)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the currently authenticated user from the JWT token.
    Raises 401 if token is invalid or user does not exist.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_email = payload.get("sub")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get the current active user.
    Can be extended to check if user is active/not banned.
    """
    # Add any additional checks here (e.g., is_active, is_banned, etc.)
    return current_user


# Note: For optional authentication, you can create a custom dependency
# that catches HTTPException from oauth2_scheme. Here's an example:
# 
# from fastapi import Security
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# 
# optional_oauth2 = HTTPBearer(auto_error=False)
# 
# def get_current_user_optional(
#     credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_oauth2),
#     db: Session = Depends(get_db)
# ) -> Optional[User]:
#     if credentials is None:
#         return None
#     token = credentials.credentials
#     payload = decode_access_token(token)
#     if payload is None:
#         return None
#     user_id: str = payload.get("sub")
#     if user_id is None:
#         return None
#     user = db.query(User).filter(User.email == user_id).first()
#     return user
