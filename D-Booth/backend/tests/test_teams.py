import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_create_team(authenticated_client: AsyncClient):
    team_data = {"name": "Test Team", "slug": "test-team", "description": "A test team"}

    response = await authenticated_client.post("/api/v1/teams", json=team_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == team_data["name"]
    assert data["slug"] == team_data["slug"]


@pytest.mark.anyio
async def test_list_teams(authenticated_client: AsyncClient):
    team_data = {"name": "Test Team", "slug": "test-team"}
    await authenticated_client.post("/api/v1/teams", json=team_data)

    response = await authenticated_client.get("/api/v1/teams")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.anyio
async def test_get_team(authenticated_client: AsyncClient):
    team_data = {"name": "Test Team", "slug": "test-team"}
    create_response = await authenticated_client.post("/api/v1/teams", json=team_data)
    team_id = create_response.json()["id"]

    response = await authenticated_client.get(f"/api/v1/teams/{team_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == team_id


@pytest.mark.anyio
async def test_update_team(authenticated_client: AsyncClient):
    team_data = {"name": "Test Team", "slug": "test-team"}
    create_response = await authenticated_client.post("/api/v1/teams", json=team_data)
    team_id = create_response.json()["id"]

    update_data = {"name": "Updated Team"}
    response = await authenticated_client.put(f"/api/v1/teams/{team_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]


@pytest.mark.anyio
async def test_delete_team(authenticated_client: AsyncClient):
    team_data = {"name": "Test Team", "slug": "test-team"}
    create_response = await authenticated_client.post("/api/v1/teams", json=team_data)
    team_id = create_response.json()["id"]

    response = await authenticated_client.delete(f"/api/v1/teams/{team_id}")
    assert response.status_code == 204

    get_response = await authenticated_client.get(f"/api/v1/teams/{team_id}")
    assert get_response.status_code == 404
