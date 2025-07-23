from flask import Blueprint, request, current_app
from app.services.purchase_item import (
    get_all_purchases,
    create_purchase,
)
from app.common.response import SuccessResponse, ErrorResponse

purchase_bp = Blueprint('purchases', __name__)

@purchase_bp.route('', methods=['GET'])
def fetch_purchases():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        current_app.logger.info("GET /api/purchases HIT")
        data = get_all_purchases(page, limit)
        return SuccessResponse.send(data, message="purchases fetched successfully")
    except Exception as e:
        current_app.logger.error(f"Error fetching purchases: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

@purchase_bp.route('', methods=['POST'])
def create_purchase_route():
    try:
        current_app.logger.info("POST /api/purchases HIT")
        data = request.get_json()
        created = create_purchase(data)
        return SuccessResponse.send(created, message="purchase created successfully")
    except Exception as e:
        current_app.logger.error(f"Error creating purchase: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=400)
