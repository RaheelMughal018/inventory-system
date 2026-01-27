from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from typing import Optional, List
from app.models.item_category import Category, generate_custom_id
from app.logger_config import logger


def get_category_by_id(db: Session, category_id: str) -> Optional[Category]:
    """Get category by ID."""
    return db.query(Category).filter(Category.id == category_id).first()


def get_category_by_name(db: Session, name: str) -> Optional[Category]:
    """Get category by name."""
    return db.query(Category).filter(Category.name == name).first()


def get_all_categories(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
) -> tuple[List[Category], int]:
    """Get all categories with optional search filtering."""
    query = db.query(Category)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Category.name.ilike(search_term),
                Category.id.ilike(search_term)
            )
        )
    
    total = query.count()
    categories = query.offset(skip).limit(limit).all()
    
    return categories, total


def create_category(
    db: Session,
    name: str
) -> Category:
    """Create a new category."""
    # Check if category with same name already exists
    existing_category = get_category_by_name(db, name)
    if existing_category:
        raise ValueError("Category with this name already exists")
    
    # Generate unique category ID
    category_id = generate_custom_id("CAT")
    
    # Ensure category_id is unique
    while get_category_by_id(db, category_id):
        category_id = generate_custom_id("CAT")
    
    # Create category
    category = Category(
        id=category_id,
        name=name
    )
    
    db.add(category)
    
    try:
        db.commit()
        db.refresh(category)
        return category
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating category: {str(e)}")
        raise ValueError("Failed to create category. Category name may already exist.")


def update_category(
    db: Session,
    category_id: str,
    name: Optional[str] = None
) -> Optional[Category]:
    """Update category information."""
    category = get_category_by_id(db, category_id)
    if not category:
        return None
    
    if name is not None:
        # Check if name is already taken by another category
        existing_category = get_category_by_name(db, name)
        if existing_category and existing_category.id != category_id:
            raise ValueError("Category name is already taken by another category")
        category.name = name
    
    try:
        db.commit()
        db.refresh(category)
        return category
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error updating category: {str(e)}")
        raise ValueError("Failed to update category.")


def delete_category(db: Session, category_id: str) -> bool:
    """Delete a category."""
    category = get_category_by_id(db, category_id)
    if not category:
        return False
    
    # Check if category has items
    if category.items:
        raise ValueError("Cannot delete category that has items. Please remove or reassign items first.")
    
    db.delete(category)
    try:
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting category: {str(e)}")
        raise ValueError("Failed to delete category.")
