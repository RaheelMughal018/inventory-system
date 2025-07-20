from flask import Blueprint, request,current_app
from app.common.response import SuccessResponse, ErrorResponse
from app.services.category import get_all_categories, create_category,delete_category as delete_category_service,update_category as update_category_service

category_bp = Blueprint('categories', __name__)

@category_bp.route('', methods=['GET'])
def fetch_categories():
    try:

        current_app.logger.info("GET /api/categories HIT...")
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        data = get_all_categories(page, limit)
        return SuccessResponse.send(data, message="Categories fetched successfully")
    except Exception as e:
        current_app.logger.error(f"Error fetching categories: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

@category_bp.route('', methods=['POST'])
def add_category():
    try:
        current_app.logger.info("POST /api/categories HIT...")
        data = request.get_json()
        new_category = create_category(data)
        return SuccessResponse.send(new_category, message="Category created successfully", status_code=201)
    except Exception as e:
        current_app.logger.error(f"Error creating category: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

@category_bp.route('/<string:category_id>', methods=['PUT'])
def update_category(category_id):
    try:
        current_app.logger.info(f"PUT /api/categories/{category_id} HIT...")
        data = request.get_json()
        updated_category = update_category_service(category_id, data)
        if not updated_category:
            return ErrorResponse.send(message="Category not found", status_code=404)
        return SuccessResponse.send(updated_category, message="Category updated successfully")
    except Exception as e:
        current_app.logger.error(f"Error updating category: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

@category_bp.route('/<string:category_id>', methods=['DELETE'])
def delete_category(category_id):
    try:
        current_app.logger.info(f"DELETE /api/categories/{category_id} HIT...")
        deleted_category = delete_category_service(category_id)
        if not deleted_category:
            return ErrorResponse.send(message="Category not found", status_code=404)
        return SuccessResponse.send(message="Category deleted successfully")
    except Exception as e:
        current_app.logger.error(f"Error deleting category: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)
