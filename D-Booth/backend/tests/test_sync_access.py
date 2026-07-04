from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.models import Booth, BoothStatus


async def _create_team(client: AsyncClient, slug: str) -> dict:
    response = await client.post(
        "/api/v1/teams",
        json={"name": f"Sync Team {slug}", "slug": f"sync-team-{slug}"},
    )
    assert response.status_code == 201
    return response.json()


async def _create_booth(db_session: AsyncSession, team_id: str, slug: str) -> Booth:
    booth = Booth(
        id=uuid4(),
        team_id=team_id,
        name=f"Sync Booth {slug}",
        device_id=f"sync-device-{slug}",
        status=BoothStatus.ONLINE,
        last_heartbeat=datetime.now(timezone.utc),
    )
    db_session.add(booth)
    await db_session.commit()
    await db_session.refresh(booth)
    return booth


async def _other_client(authenticated_client: AsyncClient) -> AsyncClient:
    other_user_data = {
        "email": "sync-other@example.com",
        "password": "OtherPass123!@",
        "full_name": "Sync Other",
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
async def test_sync_state_requires_authentication(client: AsyncClient):
    response = await client.get(
        f"/api/v1/sync/state/{uuid4()}",
        params={"team_id": str(uuid4())},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_sync_state_rejects_non_member(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
):
    team = await _create_team(authenticated_client, "non-member")
    booth = await _create_booth(db_session, team["id"], "non-member")

    async with await _other_client(authenticated_client) as other_client:
        response = await other_client.get(
            f"/api/v1/sync/state/{booth.id}",
            params={"team_id": team["id"]},
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_sync_state_allows_team_member(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
):
    team = await _create_team(authenticated_client, "member")
    booth = await _create_booth(db_session, team["id"], "member")

    response = await authenticated_client.get(
        f"/api/v1/sync/state/{booth.id}",
        params={"team_id": team["id"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["booth_id"] == str(booth.id)
    assert data["team_id"] == team["id"]


@pytest.mark.anyio
async def test_sync_log_rejects_non_member(
    authenticated_client: AsyncClient,
):
    team = await _create_team(authenticated_client, "log-non-member")

    async with await _other_client(authenticated_client) as other_client:
        response = await other_client.get(f"/api/v1/sync/log/{team['id']}")

    assert response.status_code == 403
