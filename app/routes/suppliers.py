# app/routes/supplier_routes.py

from flask import Blueprint, request
from app.services.suppliers import get_all_suppliers, create_supplier, update_supplier,delete_supplier
from app.common.response import SuccessResponse, ErrorResponse
from flask import current_app
supplier_bp = Blueprint('suppliers', __name__)

@supplier_bp.route('/', methods=['GET'])
def fetch_suppliers():
    try:
        current_app.logger.info("GET /api/suppliers  HIT...")
        data = get_all_suppliers()
        return SuccessResponse.send(data, message="Suppliers fetched successfully")
    except Exception as e:
        current_app.logger.error(f"Error fetching suppliers: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

@supplier_bp.route('/',methods=['POST'])
def create_suppliers():
    try:
        current_app.logger.info("POST /api/suppliers  HIT...")
        data = request.get_json()
        new_supplier = create_supplier(data)
        return SuccessResponse.send(new_supplier,message="Supplier created successfully")
    except Exception as e:
        current_app.logger.error(f"Error creating suppliers: {str(e)}")
        return ErrorResponse.send(message=str(e),status_code=400)

@supplier_bp.route('/<string:supplier_id>',methods=['PUT'])
def update_supplier_route(supplier_id):
    try:
        current_app.logger.info("PUT /api/suppliers/<id>  HIT...")
        data = request.get_json()
        updated = update_supplier(supplier_id, data)
        if not updated:
            return ErrorResponse.send(message="Supplier not found", status_code=404)
        return SuccessResponse.send(updated, message="Supplier updated successfully")
    except Exception as e:
        current_app.logger.error(f"Error updating supplier: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)
    
@supplier_bp.route('/<string:supplier_id>',methods=['DELETE'])
def remove_supplier(supplier_id):
    try:
        current_app.logger.info("DELETE /api/suppliers/<id>  HIT...")
        deleted = delete_supplier(supplier_id)
        return SuccessResponse.send(deleted, message="Supplier deleted successfully")
    except ValueError as ve:
        return ErrorResponse.send(message=str(ve), status_code=404)
    except Exception as e:
        current_app.logger.error(f"Error deleting supplier: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

    
