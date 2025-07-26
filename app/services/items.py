
from app.models.item import Item 
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError



def get_all_items(page, limit, search=None):
    try:
        base_query = Item.query
        if search:
            base_query = base_query.filter(Item.name.ilike(f"%{search.strip()}%"))

        paginated = base_query.paginate(page=page, per_page=limit, error_out=False)

        return {
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": paginated.page,
            "per_page": paginated.per_page,
            "data": [
                {
                    'item_id': str(c.item_id),
                    'name': c.name,
                    'type': c.type,
                    'created_at': c.created_at.isoformat() if c.created_at else None,
                    'updated_at': c.updated_at.isoformat() if c.updated_at else None
                }
                for c in paginated.items
            ]
        }
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")