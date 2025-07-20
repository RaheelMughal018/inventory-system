import uuid
from app.models.item import Item
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from app import db
from flask import current_app

def get_all_items(page, limit):
    try:
        paginated = Item.query.paginate(page=page, per_page=limit, error_out=False)
        current_app.logger.info("paginate: %s", paginated)

        return {
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": paginated.page,
            "per_page": paginated.per_page,
            "data": [
                {
                    'id': str(item.id),
                    'name': item.name,
                    'price': item.price,
                    'created_at': item.created_at.isoformat(),
                    'updated_at': item.updated_at.isoformat(),
                    'categories': [
                        {
                            'id': str(cat.id),
                            'name': cat.name,
                            'created_at': cat.created_at.isoformat(),
                            'updated_at': cat.updated_at.isoformat()
                        } for cat in item.categories
                    ]
                }
                for item in paginated.items
            ]
        }
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")

def create_item(data):
    try:
        new_item = Item(
            id=str(uuid.uuid4()),
            name=data.get('name'),
            price=data.get('price'),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(new_item)
        db.session.commit()
        return {
            'id': str(new_item.id),
            'name': new_item.name,
            'price': new_item.price,
            'created_at': new_item.created_at.isoformat(),
            'updated_at': new_item.updated_at.isoformat(),
            'categories': []  # Initially empty
        }
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred {str(e)}")
        db.session.rollback()
        raise RuntimeError(f"Database error: {str(e)}")

def update_item(item_id, data):
    try:
        item = Item.query.get(item_id)
        if not item:
            raise ValueError("Item not found")

        item.name = data.get('name', item.name)
        item.price = data.get('price', item.price)
        item.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        return {
            'id': str(item.id),
            'name': item.name,
            'price': item.price,
            'created_at': item.created_at.isoformat(),
            'updated_at': item.updated_at.isoformat(),
            'categories': [
                {
                    'id': str(cat.id),
                    'name': cat.name,
                    'created_at': cat.created_at.isoformat(),
                    'updated_at': cat.updated_at.isoformat()
                } for cat in item.categories
            ]
        }
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(f"Database error occurred {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")
    except ValueError as ve:
        current_app.logger.error(str(ve))
        raise ve

def delete_item(item_id):
    try:
        item = Item.query.get(item_id)
        if not item:
            raise ValueError("Item not found")

        db.session.delete(item)
        db.session.commit()

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception(f"Database error occurred {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")
    except ValueError as ve:
        current_app.logger.error(str(ve))
        raise ve

def get_item_by_id(item_id):
    try:
        item = Item.query.get(item_id)
        if not item:
            raise ValueError("Item not found")

        return {
            'id': str(item.id),
            'name': item.name,
            'price': item.price,
            'created_at': item.created_at.isoformat(),
            'updated_at': item.updated_at.isoformat(),
            'categories': [
                {
                    'id': str(cat.id),
                    'name': cat.name,
                    'created_at': cat.created_at.isoformat(),
                    'updated_at': cat.updated_at.isoformat()
                } for cat in item.categories
            ]
        }
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")
    except ValueError as ve:
        current_app.logger.error(str(ve))
        raise ve
