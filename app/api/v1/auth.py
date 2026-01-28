from email import message
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.dependencies import get_db
from app.core.security import create_access_token
from app.core.config import settings
from app.services.user_service import authenticate_user, create_user, get_all_users
from app.schemas.auth import LoginRequest, LoginResponse, Logout, RegisterResponse, Token, RegisterRequest
from app.logger_config import logger
from app.models.user import UserRole

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register the first user (only works if no users exist in the database).
    This endpoint is used to create the initial admin/owner user.
    """
    try:
        # Check if any users exist
        users, total = get_all_users(db, skip=0, limit=1)
        if total > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration is only allowed when no users exist. Please use the authenticated user creation endpoint."
            )

        # Create the first user
        user = create_user(
            db=db,
            email=register_data.email,
            password=register_data.password,
            name=register_data.name,
            role=UserRole.owner,
            created_by_id=None  # First user has no creator
        )

        # Create access token
        # access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        # access_token = create_access_token(
        #     data={"sub": user.email, "user_id": user.user_id, "role": user.role.value},
        #     expires_delta=access_token_expires
        # )

        logger.info(f"First user {user.email} registered successfully")

        return RegisterResponse(
            id=user.id,
            user_id=user.user_id,
            email=user.email,
            name=user.name
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )


@router.post("/login", response_model=LoginResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login endpoint - Authenticate user and return JWT token.
    """
    try:
        logger.info(f"Login attempt for email: {login_data.email}")

        # Authenticate user
        user = authenticate_user(db, login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Create access token
        access_token_expires = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.user_id,
                  "role": user.role.value},
            expires_delta=access_token_expires
        )

        logger.info(f"User {user.email} logged in successfully")

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user.id,
                "user_id": user.user_id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


@router.get("/logout", response_model=Logout)
def logout():
    """
    logout the user
    """
    logger.info("User Logged out")
    return Logout(
        message="Logged out Successfully"
    )


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token endpoint (for Swagger UI authentication).
    """
    user = authenticate_user(db, form_data.name, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.user_id, "role": user.role.value},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}
