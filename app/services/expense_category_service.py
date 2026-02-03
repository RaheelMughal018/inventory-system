from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from typing import Optional, List

from app.models.expense import ExpenseCategory
from app.models.item_category import generate_custom_id
from app.logger_config import logger


def get_expense_category_by_id(db: Session, category_id: str) -> Optional[ExpenseCategory]:
    """Get expense category by ID."""
    return db.query(ExpenseCategory).filter(ExpenseCategory.id == category_id).first()


def get_expense_category_by_name(db: Session, name: str) -> Optional[ExpenseCategory]:
    """Get expense category by name."""
    return db.query(ExpenseCategory).filter(ExpenseCategory.name == name).first()


def get_all_expense_categories(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
) -> tuple[List[ExpenseCategory], int]:
    """Get all expense categories with optional search."""
    query = db.query(ExpenseCategory)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                ExpenseCategory.name.ilike(term),
                ExpenseCategory.id.ilike(term),
            )
        )
    total = query.count()
    categories = query.offset(skip).limit(limit).all()
    return categories, total


def create_expense_category(db: Session, name: str) -> ExpenseCategory:
    """Create a new expense category."""
    existing = get_expense_category_by_name(db, name)
    if existing:
        raise ValueError("Expense category with this name already exists")
    category_id = generate_custom_id("EXPCAT")
    while get_expense_category_by_id(db, category_id):
        category_id = generate_custom_id("EXP")
    category = ExpenseCategory(id=category_id, name=name)
    db.add(category)
    try:
        db.commit()
        db.refresh(category)
        return category
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating expense category: {e}")
        raise ValueError("Failed to create expense category.")


def update_expense_category(
    db: Session,
    category_id: str,
    name: Optional[str] = None,
) -> Optional[ExpenseCategory]:
    """Update expense category."""
    category = get_expense_category_by_id(db, category_id)
    if not category:
        return None
    if name is not None:
        existing = get_expense_category_by_name(db, name)
        if existing and existing.id != category_id:
            raise ValueError("Expense category name is already taken")
        category.name = name
    try:
        db.commit()
        db.refresh(category)
        return category
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error updating expense category: {e}")
        raise ValueError("Failed to update expense category.")


def delete_expense_category(db: Session, category_id: str) -> bool:
    """Delete expense category if it has no expenses."""
    category = get_expense_category_by_id(db, category_id)
    if not category:
        return False
    if category.expenses:
        raise ValueError("Cannot delete category that has expenses. Remove or reassign expenses first.")
    db.delete(category)
    try:
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting expense category: {e}")
        raise ValueError("Failed to delete expense category.")
