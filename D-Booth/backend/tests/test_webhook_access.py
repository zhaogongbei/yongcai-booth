from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.models import WebhookLog


async def _create_team(client: AsyncClient, slug: str) -> dict:
    response = await client.post(
        "/api/v1/teams",
        json={"name": f"Webhook Team {slug}", "slug": f"webhook-team-{slug}"},
    )
    assert response.status_code == 201
    return response.json()


async def _create_webhook(client: AsyncClient, slug: str) -> dict:
    await _create_team(client, slug)
    response = await client.post(
        "/api/v1/webhooks",
        json={"url": f"https://example.test/{slug}", "events": ["photo.created"]},
    )
    assert response.status_code == 201
    return response.json()


async def _other_client(authenticated_client: AsyncClient, slug: str) -> AsyncClient:
    other_user_data = {
        "email": f"webhook-other-{slug}@example.com",
        "password": "OtherPass123!@",
        "full_name": "Webhook Other",
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


async def _create_webhook_log(db_session: AsyncSession, webhook_id: str) -> WebhookLog:
    log = WebhookLog(
        id=uuid4(),
        webhook_id=webhook_id,
        event_type="photo.created",
        payload={"photo_id": "photo-1"},
        success=True,
        response_status=200,
        response_data="ok",
        duration_ms=12,
        attempt_count=1,
        signature="sig",
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    return log


@pytest.mark.anyio
async def test_webhook_delete_requires_team_membership(
    authenticated_client: AsyncClient,
):
    webhook = await _create_webhook(authenticated_client, "delete-non-member")

    async with await _other_client(authenticated_client, "delete-non-member") as other_client:
        response = await other_client.delete(f"/api/v1/webhooks/{webhook['id']}")

    assert response.status_code == 403


@pytest.mark.anyio
async def test_team_member_can_delete_webhook(authenticated_client: AsyncClient):
    webhook = await _create_webhook(authenticated_client, "delete-member")

    response = await authenticated_client.delete(f"/api/v1/webhooks/{webhook['id']}")

    assert response.status_code == 204


@pytest.mark.anyio
async def test_webhook_logs_require_team_membership(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
):
    webhook = await _create_webhook(authenticated_client, "logs-non-member")
    await _create_webhook_log(db_session, webhook["id"])

    async with await _other_client(authenticated_client, "logs-non-member") as other_client:
        response = await other_client.get(f"/api/v1/webhooks/{webhook['id']}/logs")

    assert response.status_code == 403


@pytest.mark.anyio
async def test_team_member_can_read_webhook_logs(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
):
    webhook = await _create_webhook(authenticated_client, "logs-member")
    log = await _create_webhook_log(db_session, webhook["id"])

    response = await authenticated_client.get(f"/api/v1/webhooks/{webhook['id']}/logs")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(log.id)


@pytest.mark.anyio
async def test_missing_webhook_returns_404_for_logs(authenticated_client: AsyncClient):
    response = await authenticated_client.get(f"/api/v1/webhooks/{uuid4()}/logs")

    assert response.status_code == 404
