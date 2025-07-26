from flask import Blueprint, request
from app.services.stocks import get_all_stock
from app.common.response import SuccessResponse, ErrorResponse
from flask import current_app
stocks_bp = Blueprint('stocks', __name__)


@stocks_bp.route('/', methods=['GET'])
def fetch_stocks():
    try:
        current_app.logger.info("GET /api/stock  HIT...")
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        search = request.args.get("search", default=None, type=str)

        data = get_all_stock(page, limit, search)
        return SuccessResponse.send(data, message="stocks fetched successfully")
    except Exception as e:
        current_app.logger.error(f"Error fetching stocks: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

