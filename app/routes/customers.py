# app/routes/customer_routes.py

from flask import Blueprint, request
from app.services.customer import get_all_customers, create_customer, update_customer, delete_customer, get_customer_by_id
from app.common.response import SuccessResponse, ErrorResponse
from flask import current_app
customer_bp = Blueprint('customers', __name__)

@customer_bp.route('/', methods=['GET'])
def fetch_customers():
    try:
        current_app.logger.info("GET /api/customers  HIT...")
        data = get_all_customers()
        return SuccessResponse.send(data, message="customers fetched successfully")
    except Exception as e:
        current_app.logger.error(f"Error fetching customers: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

@customer_bp.route('/',methods=['POST'])
def create_customers():
    try:
        current_app.logger.info("POST /api/customers  HIT...")
        data = request.get_json()
        new_customer = create_customer(data)
        return SuccessResponse.send(new_customer,message="customer created successfully")
    except Exception as e:
        current_app.logger.error(f"Error creating customers: {str(e)}")
        return ErrorResponse.send(message=str(e),status_code=400)

@customer_bp.route('/<string:customer_id>',methods=['PUT'])
def update_customer_route(customer_id):
    try:
        current_app.logger.info("PUT /api/customers/<id>  HIT...")
        data = request.get_json()
        updated = update_customer(customer_id, data)
        if not updated:
            return ErrorResponse.send(message="customer not found", status_code=404)
        return SuccessResponse.send(updated, message="customer updated successfully")
    except Exception as e:
        current_app.logger.error(f"Error updating customer: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)
    
@customer_bp.route('/<string:customer_id>',methods=['DELETE'])
def remove_customer(customer_id):
    try:
        current_app.logger.info(f"DELETE /api/customers/{customer_id}  HIT...")
        deleted = delete_customer(customer_id)
        return SuccessResponse.send(deleted, message="customer deleted successfully")
    except ValueError as ve:
        return ErrorResponse.send(message=str(ve), status_code=404)
    except Exception as e:
        current_app.logger.error(f"Error deleting customer: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

@customer_bp.route('/<string:customer_id>', methods=['GET'])
def fetch_customer_by_id(customer_id):
    try:
        current_app.logger.info(f"GET /api/customers/{customer_id} HIT...")
        customer = get_customer_by_id(customer_id)
        if not customer:
            return ErrorResponse.send(message="customer not found", status_code=404)
        return SuccessResponse.send(customer, message="customer fetched successfully")
    except Exception as e:
        current_app.logger.error(f"Error fetching customer: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)


