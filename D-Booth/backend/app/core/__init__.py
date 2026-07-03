"""
D-Booth Backend Core Module

Provides core functionality including:
- Database connection and session management
- Authentication and JWT security
- Structured logging with JSON support
- Exception handling and custom exceptions
- Middleware for request tracking and performance monitoring
"""

from app.core.database import (
    Base,
    get_db,
    get_db_context,
    get_engine,
    get_session_maker,
    check_database_health,
    dispose_engine,
)

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
    get_token_jti,
    rotate_refresh_token,
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    TokenTypeMismatchError,
)

from app.core.logging import (
    setup_logging,
    shutdown_logging,
    get_logger,
    log_with_context,
    JSONFormatter,
    RequestContextFilter,
)

from app.core.exceptions import (
    BoothBaseException,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ResourceConflictError,
    ValidationException,
    DatabaseError,
    ExternalServiceError,
    RateLimitExceededError,
    FileProcessingError,
    register_exception_handlers,
    booth_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)

from app.core.middleware import (
    RequestIDMiddleware,
    PerformanceMonitoringMiddleware,
    SecurityHeadersMiddleware,
    CompressionHeaderMiddleware,
    get_request_id,
)

__all__ = [
    # Database
    "Base",
    "get_db",
    "get_db_context",
    "get_engine",
    "get_session_maker",
    "check_database_health",
    "dispose_engine",
    # Security
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token",
    "get_token_jti",
    "rotate_refresh_token",
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenTypeMismatchError",
    # Logging
    "setup_logging",
    "shutdown_logging",
    "get_logger",
    "log_with_context",
    "JSONFormatter",
    "RequestContextFilter",
    # Exceptions
    "BoothBaseException",
    "AuthenticationError",
    "AuthorizationError",
    "ResourceNotFoundError",
    "ResourceConflictError",
    "ValidationException",
    "DatabaseError",
    "ExternalServiceError",
    "RateLimitExceededError",
    "FileProcessingError",
    "register_exception_handlers",
    "booth_exception_handler",
    "http_exception_handler",
    "validation_exception_handler",
    "general_exception_handler",
    # Middleware
    "RequestIDMiddleware",
    "PerformanceMonitoringMiddleware",
    "SecurityHeadersMiddleware",
    "CompressionHeaderMiddleware",
    "get_request_id",
]
