import pytest
from httpx import AsyncClient

from app.api.v1 import auth as auth_api
from app.core.cache import RedisCache


async def _register_and_login(client: AsyncClient, user_data: dict) -> dict:
    await client.post("/api/v1/auth/register", json=user_data)
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": user_data["email"], "password": user_data["password"]},
    )
    assert response.status_code == 200
    return response.json()


class FakeRedisClient:
    """Mimics the subset of redis.asyncio.Redis used by auth revocation."""

    def __init__(self, fail_setex: bool = False, fail_exists: bool = False, exists_result: int = 0):
        self.fail_setex = fail_setex
        self.fail_exists = fail_exists
        self.exists_result = exists_result
        self.exists_calls: list[str] = []
        self.setex_calls: list[tuple[str, int, str]] = []

    async def exists(self, key: str):
        if self.fail_exists:
            raise RuntimeError("redis read failed")
        self.exists_calls.append(key)
        return self.exists_result

    async def setex(self, key: str, ttl: int, value: str):
        if self.fail_setex:
            raise RuntimeError("redis write failed")
        self.setex_calls.append((key, ttl, value))


def _patch_redis_client(monkeypatch, client):
    """Patch RedisCache.get_client to return ``client`` (or None when unavailable).

    Auth reuses the shared RedisCache client instead of opening a per-call
    connection, so tests patch the shared seam. The client is NOT closed by
    auth (it is shared app-wide), so no closed assertion is needed.
    """

    async def fake_get_client():
        return client

    monkeypatch.setattr(RedisCache, "get_client", fake_get_client)


@pytest.mark.anyio
async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]


@pytest.mark.anyio
async def test_register_user(client: AsyncClient, test_user_data):
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert "id" in data


@pytest.mark.anyio
async def test_login_success(client: AsyncClient, test_user_data):
    data = await _register_and_login(client, test_user_data)
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_invalid_password(client: AsyncClient, test_user_data):
    await client.post("/api/v1/auth/register", json=test_user_data)

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user_data["email"], "password": "WrongPassword123!"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_current_user(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert "email" in data


@pytest.mark.anyio
async def test_unauthorized_access(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_fails_when_revocation_status_unavailable(
    client: AsyncClient, test_user_data, monkeypatch
):
    tokens = await _register_and_login(client, test_user_data)
    _patch_redis_client(monkeypatch, None)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Refresh token revocation is unavailable"


@pytest.mark.anyio
async def test_refresh_fails_when_revocation_check_fails(
    client: AsyncClient, test_user_data, monkeypatch
):
    tokens = await _register_and_login(client, test_user_data)
    fake_client = FakeRedisClient(fail_exists=True)
    _patch_redis_client(monkeypatch, fake_client)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Refresh token revocation is unavailable"


@pytest.mark.anyio
async def test_refresh_rejects_revoked_token(client: AsyncClient, test_user_data, monkeypatch):
    tokens = await _register_and_login(client, test_user_data)
    fake_client = FakeRedisClient(exists_result=1)
    _patch_redis_client(monkeypatch, fake_client)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Token revoked"
    assert len(fake_client.exists_calls) == 1


@pytest.mark.anyio
async def test_refresh_revokes_old_refresh_token(client: AsyncClient, test_user_data, monkeypatch):
    tokens = await _register_and_login(client, test_user_data)
    fake_client = FakeRedisClient()
    _patch_redis_client(monkeypatch, fake_client)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"] != tokens["refresh_token"]
    # Auth reuses the shared client for both the revocation check and the write.
    assert len(fake_client.exists_calls) == 1
    assert len(fake_client.setex_calls) == 1
    check_key = fake_client.exists_calls[0]
    key, ttl, value = fake_client.setex_calls[0]
    assert key == check_key
    assert ttl > 0
    assert value == "1"


@pytest.mark.anyio
async def test_logout_fails_when_refresh_revocation_unavailable(
    client: AsyncClient, test_user_data, monkeypatch
):
    tokens = await _register_and_login(client, test_user_data)
    _patch_redis_client(monkeypatch, None)

    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Refresh token revocation is unavailable"


@pytest.mark.anyio
async def test_logout_fails_when_refresh_revocation_write_fails(
    client: AsyncClient, test_user_data, monkeypatch
):
    tokens = await _register_and_login(client, test_user_data)
    fake_client = FakeRedisClient(fail_setex=True)
    _patch_redis_client(monkeypatch, fake_client)

    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Refresh token revocation is unavailable"


@pytest.mark.anyio
async def test_logout_revokes_refresh_token(client: AsyncClient, test_user_data, monkeypatch):
    tokens = await _register_and_login(client, test_user_data)
    fake_client = FakeRedisClient()
    _patch_redis_client(monkeypatch, fake_client)

    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 204
    assert len(fake_client.setex_calls) == 1
    key, ttl, value = fake_client.setex_calls[0]
    assert key.startswith("revoked_refresh:")
    assert ttl > 0
    assert value == "1"
