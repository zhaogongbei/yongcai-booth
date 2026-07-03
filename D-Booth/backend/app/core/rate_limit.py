import asyncio
import time
from typing import Dict

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Async rate limiting middleware with memory cleanup"""

    MAX_CLIENTS = 10000  # Maximum number of tracked clients
    TRUSTED_PROXIES = {"127.0.0.1", "::1"}

    def __init__(self, app):
        super().__init__(app)
        self.requests: Dict[str, list] = {}
        self.lock = asyncio.Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Run full cleanup every 5 minutes

    def _is_trusted_proxy(self, request: Request) -> bool:
        """Check if the connecting client is a trusted proxy"""
        if not request.client:
            return False
        return request.client.host in self.TRUSTED_PROXIES

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request"""
        if self._is_trusted_proxy(request):
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
        else:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                logger.warning(
                    "Suspicious X-Forwarded-For header from untrusted client: " "client=%s xff=%s",
                    request.client.host if request.client else "unknown",
                    forwarded,
                )
        return request.client.host if request.client else "unknown"

    def _clean_old_requests(self, timestamps: list, window: int) -> list:
        """Remove timestamps older than window"""
        current_time = time.time()
        return [ts for ts in timestamps if current_time - ts < window]

    def _cleanup_expired_clients(self) -> None:
        """Remove all clients with no recent requests"""
        current_time = time.time()
        expired_clients = [
            client_id
            for client_id, timestamps in self.requests.items()
            if not timestamps or current_time - timestamps[-1] > 3600
        ]
        for client_id in expired_clients:
            del self.requests[client_id]

    async def dispatch(self, request: Request, call_next):
        whitelist = ["/health", "/metrics"]
        if request.url.path in whitelist or request.url.path.startswith("/api/v1/internal/"):
            return await call_next(request)

        client_id = self._get_client_id(request)
        current_time = time.time()

        async with self.lock:
            # Periodic full cleanup
            if current_time - self._last_cleanup > self._cleanup_interval:
                self._cleanup_expired_clients()
                self._last_cleanup = current_time

            # Initialize client if not exists
            if client_id not in self.requests:
                # Evict oldest client if at capacity
                if len(self.requests) >= self.MAX_CLIENTS:
                    oldest = min(
                        self.requests, key=lambda k: self.requests[k][-1] if self.requests[k] else 0
                    )
                    del self.requests[oldest]
                self.requests[client_id] = []

            # Clean old timestamps for this client
            self.requests[client_id] = self._clean_old_requests(self.requests[client_id], 3600)

            # Check rate limits
            minute_requests = [ts for ts in self.requests[client_id] if current_time - ts < 60]
            hour_requests = self.requests[client_id]

            if len(minute_requests) >= settings.RATE_LIMIT_PER_MINUTE:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {settings.RATE_LIMIT_PER_MINUTE} requests per minute",
                )

            if len(hour_requests) >= settings.RATE_LIMIT_PER_HOUR:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {settings.RATE_LIMIT_PER_HOUR} requests per hour",
                )

            # Add current request
            self.requests[client_id].append(current_time)

            # Store counts for headers
            minute_remaining = settings.RATE_LIMIT_PER_MINUTE - len(minute_requests) - 1
            hour_remaining = settings.RATE_LIMIT_PER_HOUR - len(hour_requests) - 1

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Limit-Hour"] = str(settings.RATE_LIMIT_PER_HOUR)
        response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, minute_remaining))
        response.headers["X-RateLimit-Remaining-Hour"] = str(max(0, hour_remaining))

        return response
