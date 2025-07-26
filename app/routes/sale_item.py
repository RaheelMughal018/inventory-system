from flask import Blueprint, request, current_app
from app.services.sale_item import get_all_sales,create_sale
from app.common.response import SuccessResponse, ErrorResponse

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('', methods=['GET'])
def fetch_purchases():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        current_app.logger.info("GET /api/sales HIT")
        data = get_all_sales(page, limit)
        return SuccessResponse.send(data, message="sales fetched successfully")
    except Exception as e:
        current_app.logger.error(f"Error fetching sales: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

@sales_bp.route('', methods=['POST'])
def create_purchase_route():
    try:
        current_app.logger.info("POST /api/sales HIT")
        data = request.get_json()
        created = create_sale(data)
        return SuccessResponse.send(created, message="sales created successfully")
    except Exception as e:
        current_app.logger.error(f"Error sales purchase: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=400)

# @purchase_bp.route('/<purchase_id>', methods=['PUT'])
# def update_purchase_status_route(purchase_id):
#     try:
#         current_app.logger.info(f"PUT /api/purchases/{purchase_id} HIT")
#         data = request.get_json()
#         update = update_purchase_status(purchase_id,data)
        
#         return SuccessResponse.send(update, message="purchase status updated successfully")
#     except Exception as e:
#         current_app.logger.error(f"Error creating purchase: {str(e)}")
#         return ErrorResponse.send(message=str(e), status_code=400)
