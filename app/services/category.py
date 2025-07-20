import uuid
from app import db
from datetime import datetime, timezone
from app.models.category import Category
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

def get_all_categories(page, limit):
    try:
        paginated = Category.query.paginate(page=page, per_page=limit, error_out=False)
        return {
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": paginated.page,
            "per_page": paginated.per_page,
            "data": [
                {
                    'id': str(category.id),
                    'name': category.name,
                    'item_id': str(category.item_id),
                    'created_at': category.created_at.isoformat() if category.created_at else None,
                    'updated_at': category.updated_at.isoformat() if category.updated_at else None
                }
                for category in paginated.items
            ]
        }
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")

def create_category(data):
    try:
        new_category = Category(
            id=str(uuid.uuid4()),
            name=data.get('name'),
            item_id=data.get('item_id'),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(new_category)
        db.session.commit()
        return {
            'id': str(new_category.id),
            'name': new_category.name,
            'item_id': str(new_category.item_id),
            'created_at': new_category.created_at.isoformat(),
            'updated_at': new_category.updated_at.isoformat()
        }
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(f"Database error occurred: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")

def update_category(category_id, data):
    try:
        category = Category.query.get(category_id)
        if not category:
            raise ValueError("Category not found")

        category.name = data.get("name", category.name)
        category.item_id = data.get("item_id", category.item_id)
        category.updated_at = datetime.now(timezone.utc)

        db.session.commit()
        return {
            'id': str(category.id),
            'name': category.name,
            'item_id': str(category.item_id),
            'created_at': category.created_at.isoformat() if category.created_at else None,
            'updated_at': category.updated_at.isoformat() if category.updated_at else None
        }
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(f"Database error occurred: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")

def delete_category(category_id):
    try:
        category = Category.query.get(category_id)
        if not category:
            raise ValueError("Category not found")

        db.session.delete(category)
        db.session.commit()
        return {
            'id': str(category.id),
            'name': category.name,
            'item_id': str(category.item_id)
        }
    except ValueError as ve:
        current_app.logger.warning(str(ve))
        raise ve
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(f"Database error occurred: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")

def get_category_by_id(category_id):
    try:
        category = Category.query.get(category_id)
        if not category:
            return None
        return {
            'id': str(category.id),
            'name': category.name,
            'item_id': str(category.item_id),
            'created_at': category.created_at.isoformat() if category.created_at else None,
            'updated_at': category.updated_at.isoformat() if category.updated_at else None
        }
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred: {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")
