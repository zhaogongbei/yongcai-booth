"""
Middleware module for D-Booth backend.

Provides request ID tracking, performance monitoring, and custom middleware
for request/response processing.
"""

import time
import logging
from typing import Callable, Optional
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID to each request.

    The request ID is:
    - Generated if not present in X-Request-ID header
    - Added to request.state for access in route handlers
    - Added to response headers for client-side tracing
    - Added to log context for correlation
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID"):
        """
        Initialize request ID middleware.

        Args:
            app: ASGI application
            header_name: Header name for request ID (default: X-Request-ID)
        """
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add request ID.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response with request ID header
        """
        # Get or generate request ID
        request_id = request.headers.get(self.header_name)
        if not request_id:
            request_id = str(uuid4())

        # Store in request state for access in handlers
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[self.header_name] = request_id

        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor request performance and log slow requests.

    Tracks:
    - Request duration
    - Status code
    - Request method and path
    - User agent
    - Client IP
    """

    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold_ms: float = 1000.0,
        log_all_requests: bool = False
    ):
        """
        Initialize performance monitoring middleware.

        Args:
            app: ASGI application
            slow_request_threshold_ms: Threshold in ms to log as slow request
            log_all_requests: Whether to log all requests (default: only slow ones)
        """
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms
        self.log_all_requests = log_all_requests

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and measure performance.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response with performance headers
        """
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Get request ID if available
        request_id = getattr(request.state, "request_id", None)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # Prepare log context
        log_extra = {
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "ip": client_ip,
        }

        # Add query params if present (excluding sensitive data)
        if request.url.query:
            log_extra["query_params"] = str(request.url.query)

        # Log based on configuration
        if duration_ms >= self.slow_request_threshold_ms:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {duration_ms:.2f}ms",
                extra=log_extra
            )
        elif self.log_all_requests:
            logger.info(
                f"{request.method} {request.url.path} - "
                f"{response.status_code} ({duration_ms:.2f}ms)",
                extra=log_extra
            )

        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Adds standard security headers like:
    - X-Content-Type-Options
    - X-Frame-Options
    - Referrer-Policy
    - Content-Security-Policy (if configured)
    """

    def __init__(
        self,
        app: ASGIApp,
        content_security_policy: Optional[str] = None,
        permissions_policy: Optional[str] = None
    ):
        """
        Initialize security headers middleware.

        Args:
            app: ASGI application
            content_security_policy: CSP header value
            permissions_policy: Permissions-Policy header value
        """
        super().__init__(app)
        self.csp = content_security_policy
        self.permissions_policy = permissions_policy

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response with security headers
        """
        response = await call_next(request)

        # Standard security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Optional CSP
        if self.csp:
            response.headers["Content-Security-Policy"] = self.csp

        # Optional Permissions-Policy
        if self.permissions_policy:
            response.headers["Permissions-Policy"] = self.permissions_policy

        return response


class CompressionHeaderMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add compression hints for responses.

    Useful when not using a reverse proxy that handles compression.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add compression hints.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response with compression hints
        """
        response = await call_next(request)

        # Add Vary header for proper caching with compression
        vary_header = response.headers.get("Vary", "")
        if vary_header:
            if "Accept-Encoding" not in vary_header:
                response.headers["Vary"] = f"{vary_header}, Accept-Encoding"
        else:
            response.headers["Vary"] = "Accept-Encoding"

        return response


def get_request_id(request: Request) -> Optional[str]:
    """
    Helper function to get request ID from request state.

    Args:
        request: FastAPI request object

    Returns:
        Request ID if available, None otherwise

    Example:
        from fastapi import Request, Depends
        @app.get("/users")
        async def get_users(request: Request):
            request_id = get_request_id(request)
            logger.info(f"Fetching users", extra={"request_id": request_id})
    """
    return getattr(request.state, "request_id", None)
