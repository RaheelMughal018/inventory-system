
from app.models.stock import Stock
from app.models.item import Item
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from flask import request
from sqlalchemy.orm import joinedload



def get_all_stock(page, limit, search=None):
    try:
        item_name = request.args.get("item_name")
        item_type = request.args.get("item_type")

        # Join Item table to allow filtering by item fields
        base_query = Stock.query.join(Item).options(joinedload(Stock.item))

        if item_name:
            base_query = base_query.filter(Item.name.ilike(f"%{item_name.strip()}%"))

        if item_type:
            base_query = base_query.filter(Item.type.ilike(f"%{item_type.strip()}%"))

            

        paginated = base_query.paginate(page=page, per_page=limit, error_out=False)

        return {
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": paginated.page,
            "per_page": paginated.per_page,
            "data": [
                {
                    'stock_id': str(c.stock_id),
                    'quantity': c.quantity,
                    'unit_price': c.unit_price,
                    'created_at': c.created_at.isoformat() if c.created_at else None,
                    'updated_at': c.updated_at.isoformat() if c.updated_at else None,
                    'item': {
                        'item_id': c.item.item_id,
                        'name': c.item.name,
                        'type': c.item.type,
                        'display': f"{c.item.name} - {c.item.type}"
                    } if c.item else None
                }
                for c in paginated.items
            ]
        }
    except SQLAlchemyError as e:
        current_app.logger.exception(f"Database error occurred {str(e)}")
        raise RuntimeError(f"Database error: {str(e)}")