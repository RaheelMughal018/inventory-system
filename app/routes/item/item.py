# app/route/item/item.py

from flask import Blueprint, request,current_app
from app.services.item.item import get_all_items,create_item,update_item,delete_item,get_item_by_id
from app.common.response import SuccessResponse, ErrorResponse


item_bp = Blueprint('items', __name__)

@item_bp.route('', methods=['GET'])
def fetch_items():
    try:
        current_app.logger.info("GET /api/items HIT...")
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        data = get_all_items(page, limit)
        return SuccessResponse.send(data, message="Items fetched successfully")
    except Exception as e:
        current_app.logger.error(f"Error fetching items: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

@item_bp.route('', methods=['POST'])
def create_item_route():
    try:
        current_app.logger.info("POST /api/items HIT...")
        data = request.json
        item = create_item(data)
        return SuccessResponse.send(item, message="Item created successfully", status_code=201)
    except Exception as e:
        current_app.logger.error(f"Error creating item: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

@item_bp.route('/<string:item_id>', methods=['PUT'])
def update_item_route(item_id):
    try:
        current_app.logger.info(f"PUT /api/items/{item_id} HIT...")
        data = request.json
        updated_item = update_item(item_id, data)
        if not updated_item:
            return ErrorResponse.send(message="Item not found", status_code=404)
        return SuccessResponse.send(updated_item, message="Item updated successfully")
    except Exception as e:
        current_app.logger.error(f"Error updating item: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)


@item_bp.route('/<string:item_id>', methods=['DELETE'])
def delete_item_route(item_id):
    try:
        current_app.logger.info(f"DELETE /api/items/{item_id} HIT...")
        deleted_item = delete_item(item_id)
        if not deleted_item:
            return ErrorResponse.send(message="Item not found", status_code=404)
        return SuccessResponse.send(message="Item deleted successfully")
    except Exception as e:
        current_app.logger.error(f"Error deleting item: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)

@item_bp.route('/<string:item_id>', methods=['GET'])
def fetch_item_by_id(item_id):
    try:
        current_app.logger.info(f"GET /api/items/{item_id} HIT...")
        item = get_item_by_id(item_id)
        if not item:
            return ErrorResponse.send(message="Item not found", status_code=404)
        return SuccessResponse.send(item, message="Item fetched successfully")
    except Exception as e:
        current_app.logger.error(f"Error fetching item: {str(e)}")
        return ErrorResponse.send(message=str(e), status_code=500)