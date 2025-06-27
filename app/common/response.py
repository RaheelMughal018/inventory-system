# app/common/response.py

from flask import jsonify

class SuccessResponse:
    @staticmethod
    def send(data=None, message="Success", status_code=200):
        response = {
            "success": True,
            "message": message,
            "data": data
        }
        return jsonify(response), status_code


class ErrorResponse:
    @staticmethod
    def send(message="An error occurred", status_code=500, errors=None):
        response = {
            "success": False,
            "message": message,
            "errors": errors if errors else []
        }
        return jsonify(response), status_code
