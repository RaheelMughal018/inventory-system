from sqlalchemy.orm import Session
from app.models.item_category import Category, Item
from app.schemas.item import ItemCreate, ItemUpdate
from fastapi import HTTPException


class ItemService:
    @staticmethod
    def get_item_by_id(db: Session, item_id: str):

        item = db.query(Item).filter(Item.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item

    @staticmethod
    def get_all_items(db: Session, skip: int = 0, limit: int = 10, search: str = None):
        query = db.query(Item)

        if search:
            query = query.filter(Item.name.ilike(f"%{search}%"))

        total = query.count()
        items = query.offset(skip).limit(limit).all()

        return {"total": total, "items": items}

    @staticmethod
    def create_item(db: Session, item: ItemCreate):
        """Create new item"""
        # Verify category exists
        category = db.query(Category).filter(
            Category.id == item.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        new_item = Item(
            name=item.name,
            category_id=item.category_id,
            type=item.type,
            unit_type=item.unit_type,
            avg_price=item.avg_price or 0
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item

    @staticmethod
    def update_item(db: Session, item_id: str, item_data: ItemUpdate):
        """Update item by ID"""
        item = ItemService.get_item_by_id(db, item_id)

        # Verify category exists if updating
        if item_data.category_id:
            category = db.query(Category).filter(
                Category.id == item_data.category_id).first()
            if not category:
                raise HTTPException(
                    status_code=404, detail="Category not found")

        update_data = item_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(item, key, value)

        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def delete_item(db: Session, item_id: str):
        """Delete item by ID"""
        item = ItemService.get_item_by_id(db, item_id)
        db.delete(item)
        db.commit()
        return {"message": f"Item {item_id} deleted successfully"}
