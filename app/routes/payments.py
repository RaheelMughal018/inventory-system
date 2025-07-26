from flask import Blueprint, request, current_app
from app.services.payments import get_all_payments
from app.common.response import SuccessResponse, ErrorResponse

payment_bp = Blueprint('payments', __name__)

@payment_bp.route('', methods=['GET'])
def fetch_all_payments():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        current_app.logger.info("GET /api/payments HIT")
        data = get_all_payments(page, limit)
        return SuccessResponse.send(data, message="Payments fetched successfully")
    except Exception as e:
        current_app.logger.error(f"Error fetching payments: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)
