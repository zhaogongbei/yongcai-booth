import pytest
from httpx import AsyncClient


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
    await client.post("/api/v1/auth/register", json=test_user_data)

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user_data["email"], "password": test_user_data["password"]},
    )
    assert response.status_code == 200
    data = response.json()
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
