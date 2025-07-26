from flask import Blueprint, request
from app.services.items import get_all_items 
from app.common.response import SuccessResponse, ErrorResponse
from flask import current_app
items_bp = Blueprint('items', __name__)


@items_bp.route('/', methods=['GET'])
def fetch_items():
    try:
        current_app.logger.info("GET /api/items  HIT...")
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        search = request.args.get("search", default=None, type=str)

        data = get_all_items(page, limit, search)
        return SuccessResponse.send(data, message="items fetched successfully")
    except Exception as e:
        current_app.logger.error(f"Error fetching items: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

