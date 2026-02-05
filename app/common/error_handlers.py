from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
import logging

logger = logging.getLogger(__name__)

def _json_serializable(obj):
    """Convert object to JSON-serializable form (e.g. Exception -> str)."""
    if isinstance(obj, Exception):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_serializable(i) for i in obj]
    return obj


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions (404, 400, etc.). Ensure detail is JSON-serializable."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": _json_serializable(exc.detail),
            "status_code": exc.status_code,
            "error": type(exc).__name__
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors. Sanitize errors so no Exception objects are serialized."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation Error",
            "errors": _json_serializable(exc.errors()),
            "status_code": 422
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    logger.exception("Unhandled exception occurred", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal Server Error",
            "details": str(exc),
            "status_code": 500
        }
    )

def register_error_handlers(app):
    """Register error handlers with FastAPI app"""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
