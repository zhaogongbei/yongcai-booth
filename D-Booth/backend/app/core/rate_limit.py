import asyncio
import time
from typing import Dict, Optional, Tuple

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.cache import RedisCache
from app.core.config import settings
from app.core.logging import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Async rate limiting middleware.

    Uses Redis (``INCR`` + ``EXPIRE`` fixed-window counters) when available so
    that limits are shared across workers/instances. Falls back to an
    in-process memory counter when Redis is unreachable — this fallback only
    works for single-node/dev deployments.
    """

    MAX_CLIENTS = 10000  # Maximum number of tracked clients (in-memory fallback)
    TRUSTED_PROXIES = {"127.0.0.1", "::1"}

    def __init__(self, app):
        super().__init__(app)
        # In-memory fallback state (used only when Redis is unavailable)
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
                    "Suspicious X-Forwarded-For header from untrusted client: "
                    "client=%s xff=%s",
                    request.client.host if request.client else "unknown",
                    forwarded,
                )
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _window_key(client_id: str, bucket: int, suffix: str) -> str:
        return f"rl:{client_id}:{suffix}:{bucket}"

    async def _check_redis(
        self, client_id: str, current_time: float
    ) -> Optional[Tuple[int, int]]:
        """Redis-backed rate-limit check.

        Atomically increments fixed-window counters via INCR and sets a TTL on
        the first request of each window. Returns (minute_remaining,
        hour_remaining) or None when Redis is unavailable (so the caller falls
        back to in-memory accounting).
        """
        client = await RedisCache.get_client()
        if client is None:
            return None

        minute_bucket = int(current_time // 60)
        hour_bucket = int(current_time // 3600)
        minute_key = self._window_key(client_id, minute_bucket, "min")
        hour_key = self._window_key(client_id, hour_bucket, "hr")

        try:
            minute_count = await client.incr(minute_key)
            if minute_count == 1:
                await client.expire(minute_key, 60)
            hour_count = await client.incr(hour_key)
            if hour_count == 1:
                await client.expire(hour_key, 3600)
        except Exception as e:
            logger.warning(f"Redis rate-limit check failed, falling back to memory: {e}")
            return None

        return (
            settings.RATE_LIMIT_PER_MINUTE - minute_count,
            settings.RATE_LIMIT_PER_HOUR - hour_count,
        )

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

    async def _check_in_memory(
        self, client_id: str, current_time: float
    ) -> Tuple[int, int]:
        """In-process fallback (single-worker/dev only).

        Preserves the original check-then-record semantics: a request that is
        rejected does not consume a slot.
        """
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
                        self.requests,
                        key=lambda k: self.requests[k][-1] if self.requests[k] else 0,
                    )
                    del self.requests[oldest]
                self.requests[client_id] = []

            # Clean old timestamps for this client
            self.requests[client_id] = self._clean_old_requests(self.requests[client_id], 3600)

            # Check rate limits
            minute_requests = [ts for ts in self.requests[client_id] if current_time - ts < 60]
            hour_requests = self.requests[client_id]

            # Remaining slots if this request is counted (matches the Redis INCR
            # semantics: the Nth request in a window has remaining = LIMIT - N).
            minute_remaining = settings.RATE_LIMIT_PER_MINUTE - len(minute_requests) - 1
            hour_remaining = settings.RATE_LIMIT_PER_HOUR - len(hour_requests) - 1

            # Reject without recording if over limit
            if minute_remaining < 0 or hour_remaining < 0:
                return minute_remaining, hour_remaining

            # Record this request
            self.requests[client_id].append(current_time)
            return minute_remaining, hour_remaining

    async def dispatch(self, request: Request, call_next):
        whitelist = ["/health", "/metrics"]
        if request.url.path in whitelist or request.url.path.startswith("/api/v1/internal/"):
            return await call_next(request)

        client_id = self._get_client_id(request)
        current_time = time.time()

        # Prefer shared Redis counters; fall back to in-memory when Redis is down.
        result = await self._check_redis(client_id, current_time)
        if result is None:
            result = await self._check_in_memory(client_id, current_time)

        minute_remaining, hour_remaining = result

        if minute_remaining < 0:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded: {settings.RATE_LIMIT_PER_MINUTE} requests per minute"
                },
            )
        if hour_remaining < 0:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded: {settings.RATE_LIMIT_PER_HOUR} requests per hour"
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Limit-Hour"] = str(settings.RATE_LIMIT_PER_HOUR)
        response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, minute_remaining))
        response.headers["X-RateLimit-Remaining-Hour"] = str(max(0, hour_remaining))

        return response
