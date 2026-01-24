from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from app.models.user import User, UserRole, UserProfile
from app.core.security import get_password_hash, verify_password
from app.logger_config import logger


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by database ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_user_id(db: Session, user_id: str) -> Optional[User]:
    """Get user by user_id (e.g., 'OWN-ABC12345')."""
    return db.query(User).filter(User.user_id == user_id).first()


def get_all_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None,
    search: Optional[str] = None
) -> tuple[List[User], int]:
    """Get all users with optional filtering."""
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_term)) |
            (User.email.ilike(search_term)) |
            (User.user_id.ilike(search_term))
        )
    
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    
    return users, total


def create_user(
    db: Session,
    email: str,
    password: str,
    name: str,
    role: UserRole,
    created_by_id: Optional[int] = None
) -> User:
    """Create a new user."""
    # Check if user already exists
    existing_user = get_user_by_email(db, email)
    if existing_user:
        raise ValueError("User with this email already exists")
    
    # Generate unique user_id
    user_id = User.generate_user_id(role)
    
    # Ensure user_id is unique
    while get_user_by_user_id(db, user_id):
        user_id = User.generate_user_id(role)
    
    # Hash password
    password_hash = get_password_hash(password)
    
    # Create user
    user = User(
        user_id=user_id,
        email=email,
        password_hash=password_hash,
        name=name,
        role=role,
        created_by_id=created_by_id
    )
    
    db.add(user)
    db.flush()  # Flush to get user.id
    
    # Create user profile
    profile = UserProfile(user_id=user.id)
    db.add(profile)
    
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise ValueError("Failed to create user. User ID or email may already exist.")


def update_user(
    db: Session,
    user_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    role: Optional[UserRole] = None
) -> Optional[User]:
    """Update user information."""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    if name is not None:
        user.name = name
    if email is not None:
        # Check if email is already taken by another user
        existing_user = get_user_by_email(db, email)
        if existing_user and existing_user.id != user_id:
            raise ValueError("Email is already taken by another user")
        user.email = email
    if role is not None:
        user.role = role
    
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error updating user: {str(e)}")
        raise ValueError("Failed to update user.")


def change_password(
    db: Session,
    user_id: int,
    old_password: str,
    new_password: str
) -> bool:
    """Change user password."""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    # Verify old password
    if not verify_password(old_password, user.password_hash):
        raise ValueError("Invalid old password")
    
    # Update password
    user.password_hash = get_password_hash(new_password)
    
    try:
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error changing password: {str(e)}")
        raise ValueError("Failed to change password.")


def delete_user(db: Session, user_id: int) -> bool:
    """Delete a user."""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    db.delete(user)
    try:
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        raise ValueError("Failed to delete user.")


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    return user
