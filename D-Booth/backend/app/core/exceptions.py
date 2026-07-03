"""
Exception handling module for D-Booth backend.

Provides custom exceptions and unified exception handlers with
structured error responses and logging.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# Custom Exception Classes


class BoothBaseException(Exception):
    """Base exception class for all D-Booth custom exceptions."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize base exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code
            error_code: Machine-readable error code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(BoothBaseException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_FAILED",
            **kwargs,
        )


class AuthorizationError(BoothBaseException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_FAILED",
            **kwargs,
        )


class ResourceNotFoundError(BoothBaseException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, resource_id: Any, **kwargs):
        message = f"{resource} with id '{resource_id}' not found"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "resource_id": str(resource_id)},
            **kwargs,
        )


class ResourceConflictError(BoothBaseException):
    """Raised when resource creation/update conflicts with existing data."""

    def __init__(self, message: str = "Resource conflict", **kwargs):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_CONFLICT",
            **kwargs,
        )


class ValidationException(BoothBaseException):
    """Raised when business logic validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field_errors: Optional[List[Dict[str, str]]] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if field_errors:
            details["field_errors"] = field_errors
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details,
            **kwargs,
        )


class DatabaseError(BoothBaseException):
    """Raised when database operations fail."""

    def __init__(self, message: str = "Database operation failed", **kwargs):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            **kwargs,
        )


class ExternalServiceError(BoothBaseException):
    """Raised when external service integration fails."""

    def __init__(self, service: str, message: str = "External service error", **kwargs):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service},
            **kwargs,
        )


class RateLimitExceededError(BoothBaseException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None, **kwargs
    ):
        details = kwargs.pop("details", {})
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
            **kwargs,
        )


class FileProcessingError(BoothBaseException):
    """Raised when file processing fails."""

    def __init__(self, message: str = "File processing failed", **kwargs):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="FILE_PROCESSING_ERROR",
            **kwargs,
        )


# Exception Handlers


async def booth_exception_handler(request: Request, exc: BoothBaseException) -> JSONResponse:
    """
    Handle all custom D-Booth exceptions.

    Args:
        request: FastAPI request object
        exc: Custom exception instance

    Returns:
        JSON response with error details
    """
    logger.warning(
        f"{exc.error_code}: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "method": request.method,
            "path": str(request.url.path),
            "error_code": exc.error_code,
            "details": exc.details,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "status_code": exc.status_code,
                "details": exc.details,
            }
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle standard HTTP exceptions.

    Args:
        request: FastAPI request object
        exc: HTTP exception instance

    Returns:
        JSON response with error details
    """
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "method": request.method,
            "path": str(request.url.path),
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": exc.detail, "type": "http_error"}},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors from request parsing.

    Args:
        request: FastAPI request object
        exc: Validation error instance

    Returns:
        JSON response with detailed validation errors
    """
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(x) for x in error["loc"][1:]) or "body"
        errors.append(
            {
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            }
        )

    logger.warning(
        f"Validation error: {len(errors)} field(s)",
        extra={
            "method": request.method,
            "path": str(request.url.path),
            "error_count": len(errors),
            "errors": errors,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "type": "validation_error",
                "details": {"errors": errors},
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all uncaught exceptions.

    Args:
        request: FastAPI request object
        exc: Exception instance

    Returns:
        JSON response with generic error message (details hidden in production)
    """
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "method": request.method,
            "path": str(request.url.path),
            "exception_type": type(exc).__name__,
        },
        exc_info=True,
    )

    # Hide internal error details in production
    from app.core.config import settings

    if settings.DEBUG:
        error_message = f"Internal server error: {str(exc)}"
        details = {"exception": type(exc).__name__}
    else:
        error_message = "An internal server error occurred"
        details = {}

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": error_message,
                "type": "server_error",
                "details": details,
            }
        },
    )


def register_exception_handlers(app) -> None:
    """
    Register all exception handlers with FastAPI app.

    Args:
        app: FastAPI application instance

    Example:
        from fastapi import FastAPI
        app = FastAPI()
        register_exception_handlers(app)
    """
    app.add_exception_handler(BoothBaseException, booth_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
