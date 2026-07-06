"""Tests for the Redis-backed rate limiter."""

import pytest
from httpx import AsyncClient

from app.core.cache import RedisCache
from app.core import rate_limit as rl_mod


class _FakeRateLimitRedis:
    """Mimics the subset of redis.asyncio.Redis used by RateLimitMiddleware."""

    def __init__(self):
        self.counts: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, ttl: int) -> bool:
        return True


def _patch_rate_limit_redis(monkeypatch, client):
    async def fake_get_client():
        return client

    monkeypatch.setattr(RedisCache, "get_client", fake_get_client)


@pytest.mark.anyio
async def test_rate_limit_allows_under_threshold(client: AsyncClient, monkeypatch):
    _patch_rate_limit_redis(monkeypatch, _FakeRateLimitRedis())
    monkeypatch.setattr(rl_mod.settings, "RATE_LIMIT_PER_MINUTE", 3)
    monkeypatch.setattr(rl_mod.settings, "RATE_LIMIT_PER_HOUR", 100000)

    r1 = await client.get("/")
    r2 = await client.get("/")
    r3 = await client.get("/")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200
    # Remaining header reflects the last allowed request (3rd → 0 remaining).
    assert r3.headers.get("X-RateLimit-Remaining-Minute") == "0"


@pytest.mark.anyio
async def test_rate_limit_blocks_over_threshold(client: AsyncClient, monkeypatch):
    _patch_rate_limit_redis(monkeypatch, _FakeRateLimitRedis())
    monkeypatch.setattr(rl_mod.settings, "RATE_LIMIT_PER_MINUTE", 2)
    monkeypatch.setattr(rl_mod.settings, "RATE_LIMIT_PER_HOUR", 100000)

    r1 = await client.get("/")
    r2 = await client.get("/")
    r3 = await client.get("/")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429


@pytest.mark.anyio
async def test_rate_limit_whitelists_health(client: AsyncClient, monkeypatch):
    """/health is whitelisted and must not be rate-limited."""
    _patch_rate_limit_redis(monkeypatch, _FakeRateLimitRedis())
    monkeypatch.setattr(rl_mod.settings, "RATE_LIMIT_PER_MINUTE", 1)
    monkeypatch.setattr(rl_mod.settings, "RATE_LIMIT_PER_HOUR", 1)

    # Even with a limit of 1, health checks are exempt.
    r1 = await client.get("/health")
    r2 = await client.get("/health")

    assert r1.status_code == 200
    assert r2.status_code == 200
