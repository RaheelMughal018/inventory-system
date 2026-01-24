from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from typing import Optional, List
from app.models.user import User, UserRole, UserProfile
from app.core.security import get_password_hash
from app.logger_config import logger


def get_supplier_by_id(db: Session, supplier_id: int) -> Optional[User]:
    """Get supplier by database ID (must have supplier role)."""
    user = db.query(User).filter(User.id == supplier_id, User.role == UserRole.supplier).first()
    return user


def get_supplier_by_user_id(db: Session, user_id: str) -> Optional[User]:
    """Get supplier by user_id (e.g., 'SUP-ABC12345')."""
    user = db.query(User).filter(User.user_id == user_id, User.role == UserRole.supplier).first()
    return user


def get_supplier_by_email(db: Session, email: str) -> Optional[User]:
    """Get supplier by email (must have supplier role)."""
    user = db.query(User).filter(User.email == email, User.role == UserRole.supplier).first()
    return user


def get_all_suppliers(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
) -> tuple[List[User], int]:
    """Get all suppliers with optional search filtering."""
    query = db.query(User).filter(User.role == UserRole.supplier)
    
    if search:
        search_term = f"%{search}%"
        # Use left outer join to include suppliers without profiles
        query = query.outerjoin(UserProfile, User.id == UserProfile.user_id).filter(
            or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term),
                User.user_id.ilike(search_term),
                UserProfile.company_name.ilike(search_term)
            )
        )
    
    total = query.count()
    suppliers = query.offset(skip).limit(limit).all()
    
    return suppliers, total


def create_supplier(
    db: Session,
    name: str,
    company_name: Optional[str] = None,
    phone: Optional[str] = None,
    city: Optional[str] = None,
    created_by_id: Optional[int] = None
) -> User:
    """Create a new supplier."""
    # Generate unique user_id
    user_id = User.generate_user_id(UserRole.supplier)
    
    # Ensure user_id is unique
    while db.query(User).filter(User.user_id == user_id).first():
        user_id = User.generate_user_id(UserRole.supplier)
    
    
    # Create user with supplier role
    user = User(
        user_id=user_id,
        email=None,
        password_hash=None,
        name=name,
        role=UserRole.supplier,
        created_by_id=created_by_id
    )
    
    db.add(user)
    db.flush()  # Flush to get user.id
    
    # Create user profile with supplier-specific data
    profile = UserProfile(
        user_id=user.id,
        company_name=company_name,
        phone=phone,
        city=city
    )
    db.add(profile)
    
    try:
        db.commit()
        db.refresh(user)
        db.refresh(profile)
        return user
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating supplier: {str(e)}")
        raise ValueError("Failed to create supplier. User ID or email may already exist.")


def update_supplier(
    db: Session,
    supplier_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    company_name: Optional[str] = None,
    phone: Optional[str] = None,
    city: Optional[str] = None
) -> Optional[User]:
    """Update supplier information."""
    user = get_supplier_by_id(db, supplier_id)
    if not user:
        return None
    
    if name is not None:
        user.name = name
    if email is not None:
        # Check if email is already taken by another user
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user and existing_user.id != supplier_id:
            raise ValueError("Email is already taken by another user")
        user.email = email
    
    # Update profile information
    if user.profile:
        if company_name is not None:
            user.profile.company_name = company_name
        if phone is not None:
            user.profile.phone = phone
        if city is not None:
            user.profile.city = city
    else:
        # Create profile if it doesn't exist
        profile = UserProfile(
            user_id=user.id,
            company_name=company_name,
            phone=phone,
            city=city
        )
        db.add(profile)
    
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error updating supplier: {str(e)}")
        raise ValueError("Failed to update supplier.")


def delete_supplier(db: Session, supplier_id: int) -> bool:
    """Delete a supplier."""
    user = get_supplier_by_id(db, supplier_id)
    if not user:
        return False
    
    db.delete(user)
    try:
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting supplier: {str(e)}")
        raise ValueError("Failed to delete supplier.")
