from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _create_team(client: AsyncClient, slug: str) -> dict:
    response = await client.post(
        "/api/v1/teams",
        json={"name": f"Booth Team {slug}", "slug": f"booth-team-{slug}"},
    )
    assert response.status_code == 201
    return response.json()


async def _create_event(client: AsyncClient, team_id: str, slug: str) -> dict:
    response = await client.post(
        "/api/v1/events",
        json={
            "name": f"Booth Event {slug}",
            "team_id": team_id,
            "start_date": "2026-07-01T10:00:00Z",
            "end_date": "2026-07-01T18:00:00Z",
        },
    )
    assert response.status_code == 201
    return response.json()


async def _register_booth(client: AsyncClient, team_id: str, slug: str) -> dict:
    response = await client.post(
        "/api/v1/booths/register",
        json={
            "team_id": team_id,
            "name": f"Booth {slug}",
            "device_id": f"device-{slug}",
        },
    )
    assert response.status_code == 200
    return response.json()


async def _other_client(authenticated_client: AsyncClient, slug: str) -> AsyncClient:
    other_user_data = {
        "email": f"booth-other-{slug}@example.com",
        "password": "OtherPass123!@",
        "full_name": "Booth Other",
    }
    await authenticated_client.post("/api/v1/auth/register", json=other_user_data)
    login_response = await authenticated_client.post(
        "/api/v1/auth/login",
        data={"username": other_user_data["email"], "password": other_user_data["password"]},
    )
    other_token = login_response.json()["access_token"]
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {other_token}"},
    )


@pytest.mark.anyio
async def test_register_and_list_booths_use_service_instance(authenticated_client: AsyncClient):
    team = await _create_team(authenticated_client, "register")

    booth = await _register_booth(authenticated_client, team["id"], "register")
    list_response = await authenticated_client.get(
        "/api/v1/booths",
        params={"team_id": team["id"]},
    )

    assert booth["team_id"] == team["id"]
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [booth["id"]]


@pytest.mark.anyio
async def test_register_booth_rejects_non_member_team(
    authenticated_client: AsyncClient,
):
    team = await _create_team(authenticated_client, "register-non-member")

    async with await _other_client(authenticated_client, "register") as other_client:
        response = await other_client.post(
            "/api/v1/booths/register",
            json={
                "team_id": team["id"],
                "name": "Unauthorized Booth",
                "device_id": "device-register-non-member",
            },
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_get_update_delete_and_heartbeat_reject_non_member(
    authenticated_client: AsyncClient,
):
    team = await _create_team(authenticated_client, "non-member")
    booth = await _register_booth(authenticated_client, team["id"], "non-member")

    async with await _other_client(authenticated_client, "manage") as other_client:
        get_response = await other_client.get(f"/api/v1/booths/{booth['id']}")
        update_response = await other_client.put(
            f"/api/v1/booths/{booth['id']}",
            json={"name": "Cross Team Rename"},
        )
        heartbeat_response = await other_client.post(f"/api/v1/booths/{booth['id']}/heartbeat")
        delete_response = await other_client.delete(f"/api/v1/booths/{booth['id']}")

    assert get_response.status_code == 403
    assert update_response.status_code == 403
    assert heartbeat_response.status_code == 403
    assert delete_response.status_code == 403


@pytest.mark.anyio
async def test_update_booth_rejects_event_from_another_team(
    authenticated_client: AsyncClient,
):
    team_one = await _create_team(authenticated_client, "event-one")
    team_two = await _create_team(authenticated_client, "event-two")
    booth = await _register_booth(authenticated_client, team_one["id"], "event-owner")
    other_event = await _create_event(authenticated_client, team_two["id"], "event-other-team")

    response = await authenticated_client.put(
        f"/api/v1/booths/{booth['id']}",
        json={"current_event_id": other_event["id"]},
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "活动不属于该团队"


@pytest.mark.anyio
async def test_register_booth_rejects_missing_event(authenticated_client: AsyncClient):
    team = await _create_team(authenticated_client, "missing-event")

    response = await authenticated_client.post(
        "/api/v1/booths/register",
        json={
            "team_id": team["id"],
            "name": "Booth Missing Event",
            "device_id": "device-missing-event",
            "current_event_id": str(uuid4()),
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "活动不存在"
