"""
Custom exceptions and error handlers for the application.
Provides structured error responses.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from bson.errors import InvalidId
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


class APIException(Exception):
    """Base API exception class."""
    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or f"ERR_{status_code}"
        super().__init__(self.message)


class NotFoundException(APIException):
    """Resource not found exception."""
    def __init__(self, resource: str, resource_id: str = None):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message, status_code=404, error_code="NOT_FOUND")


class ValidationException(APIException):
    """Validation exception."""
    def __init__(self, message: str, errors: dict = None):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR")
        self.errors = errors or {}


class UnauthorizedException(APIException):
    """Unauthorized access exception."""
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(message, status_code=401, error_code="UNAUTHORIZED")


class ForbiddenException(APIException):
    """Forbidden access exception."""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403, error_code="FORBIDDEN")


async def api_exception_handler(request: Request, exc: APIException):
    """Handle API exceptions."""
    logger.error(f"API Exception: {exc.message} (Code: {exc.error_code}, Status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            "status_code": exc.status_code
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    errors = exc.errors()
    error_details = {}
    
    for error in errors:
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        error_details[field] = error["msg"]
    
    logger.warning(f"Validation error: {error_details}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "error_code": "VALIDATION_ERROR",
            "errors": error_details
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP Exception: {exc.detail} (Status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "status_code": exc.status_code
        }
    )


async def invalid_id_handler(request: Request, exc: InvalidId):
    """Handle invalid MongoDB ObjectId errors."""
    logger.warning(f"Invalid ObjectId: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "detail": "Invalid ID format",
            "error_code": "INVALID_ID",
            "status_code": 400
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "status_code": 500
        }
    )


