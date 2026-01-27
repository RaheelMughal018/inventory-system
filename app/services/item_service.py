from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from typing import Optional, List
from decimal import Decimal
from app.models.item_category import Item, ItemType, UnitType, generate_custom_id
from app.services.category_service import get_category_by_id
from app.logger_config import logger


def get_item_by_id(db: Session, item_id: str) -> Optional[Item]:
    """Get item by ID."""
    return ( db.query(Item)
            .options(joinedload(Item.category))
            .filter(Item.id == item_id).first()
    )

def get_item_by_name(db: Session, name: str) -> Optional[Item]:
    """Get item by name."""
    return (db.query(Item)
    .options(joinedload(Item.category))
    .filter(Item.name == name)
    .first())


def get_all_items(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    item_type: Optional[ItemType] = None
) -> tuple[List[Item], int]:
    """Get all items with optional filtering."""
    query = db.query(Item).options(joinedload(Item.category))
    
    if category_id:
        query = query.filter(Item.category_id == category_id)
    
    if item_type:
        query = query.filter(Item.type == item_type)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Item.name.ilike(search_term),
                Item.id.ilike(search_term)
            )
        )
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return items, total


def create_item(
    db: Session,
    name: str,
    type: ItemType,
    unit_type: UnitType,
    category_id: str,
    avg_price: Optional[Decimal] = None,
    total_quantity: Optional[int] = None
) -> Item:
    """Create a new item."""
    # Check if category exists
    category = get_category_by_id(db, category_id)
    if not category:
        raise ValueError("Category not found")
    
    # Generate unique item ID
    item_id = generate_custom_id("ITM")
    
    # Ensure item_id is unique
    while get_item_by_id(db, item_id):
        item_id = generate_custom_id("ITM")
    
    # Create item
    item = Item(
        id=item_id,
        name=name,
        type=type,
        unit_type=unit_type,
        category_id=category_id,
        avg_price=avg_price or Decimal("0.00"),
        total_quantity=total_quantity or 0
    )
    
    db.add(item)
    
    try:
        db.commit()
        db.refresh(item)
        return item
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating item: {str(e)}")
        raise ValueError("Failed to create item.")


def update_item(
    db: Session,
    item_id: str,
    name: Optional[str] = None,
    type: Optional[ItemType] = None,
    unit_type: Optional[UnitType] = None,
    category_id: Optional[str] = None,
    avg_price: Optional[Decimal] = None,
    total_quantity: Optional[int] = None
) -> Optional[Item]:
    """Update item information."""
    item = get_item_by_id(db, item_id)
    if not item:
        return None
    
    if name is not None:
        item.name = name
    if type is not None:
        item.type = type
    if unit_type is not None:
        item.unit_type = unit_type
    if category_id is not None:
        # Check if category exists
        category = get_category_by_id(db, category_id)
        if not category:
            raise ValueError("Category not found")
        item.category_id = category_id
    if avg_price is not None:
        item.avg_price = avg_price
    if total_quantity is not None:
        item.total_quantity = total_quantity
    
    try:
        db.commit()
        db.refresh(item)
        return item
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error updating item: {str(e)}")
        raise ValueError("Failed to update item.")


def delete_item(db: Session, item_id: str) -> bool:
    """Delete an item."""
    item = get_item_by_id(db, item_id)
    if not item:
        return False
    
    # Check if item has stock entries
    if item.stock_entry:
        raise ValueError("Cannot delete item that has stock entries. Please remove stock entries first.")
    
    db.delete(item)
    try:
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting item: {str(e)}")
        raise ValueError("Failed to delete item.")
