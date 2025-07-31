from flask import jsonify
from werkzeug.exceptions import HTTPException
import traceback
import logging

def register_error_handlers(app):
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log the exception with traceback
        app.logger.exception("Unhandled exception occurred")

        # Handle HTTP (e.g. 404, 400)
        if isinstance(e, HTTPException):
            return jsonify({
                "success": False,
                "message": e.description,
                "status_code": e.code,
                "error": e.name
            }), e.code

        # Handle all other exceptions (coding, DB errors, etc.)
        return jsonify({
            "success": False,
            "message": "Internal Server Error",
            "details": str(e),
            "status_code": 500
        }), 500
