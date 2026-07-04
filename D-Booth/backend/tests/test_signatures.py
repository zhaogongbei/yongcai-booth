from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.models import Signature


async def _create_event(client: AsyncClient, slug: str) -> dict:
    team_response = await client.post(
        "/api/v1/teams",
        json={"name": f"Signature Team {slug}", "slug": f"signature-team-{slug}"},
    )
    assert team_response.status_code == 201

    event_response = await client.post(
        "/api/v1/events",
        json={
            "name": f"Signature Event {slug}",
            "team_id": team_response.json()["id"],
            "start_date": "2026-07-01T10:00:00Z",
            "end_date": "2026-07-01T18:00:00Z",
        },
    )
    assert event_response.status_code == 201
    return event_response.json()


async def _create_session(client: AsyncClient, slug: str) -> dict:
    event = await _create_event(client, slug)
    session_response = await client.post(
        "/api/v1/photos/sessions",
        json={"event_id": event["id"], "email": f"signature-{slug}@example.com"},
    )
    assert session_response.status_code == 201
    return session_response.json()


async def _create_signature(db_session: AsyncSession, session_id: str) -> Signature:
    signature = Signature(
        id=uuid4(),
        session_id=session_id,
        signature_url="https://example.test/signature.png",
    )
    db_session.add(signature)
    await db_session.commit()
    await db_session.refresh(signature)
    return signature


async def _other_client(authenticated_client: AsyncClient, slug: str) -> AsyncClient:
    other_user_data = {
        "email": f"signature-other-{slug}@example.com",
        "password": "OtherPass123!@",
        "full_name": "Signature Other",
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
async def test_upload_signature_rejects_non_png_with_400(client: AsyncClient):
    response = await client.post(
        f"/api/v1/signatures?session_id={uuid4()}",
        files={"signature_file": ("signature.jpg", b"not a png", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "仅支持PNG格式的签名"


@pytest.mark.anyio
async def test_upload_signature_returns_404_for_missing_session(client: AsyncClient):
    response = await client.post(
        f"/api/v1/signatures?session_id={uuid4()}",
        files={"signature_file": ("signature.png", b"png", "image/png")},
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Session not found"


@pytest.mark.anyio
async def test_get_session_signatures_requires_authentication(client: AsyncClient):
    response = await client.get(f"/api/v1/signatures/session/{uuid4()}")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_and_delete_signature_reject_non_member(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
):
    session = await _create_session(authenticated_client, "non-member")
    signature = await _create_signature(db_session, session["id"])

    async with await _other_client(authenticated_client, "non-member") as other_client:
        get_response = await other_client.get(f"/api/v1/signatures/session/{session['id']}")
        delete_response = await other_client.delete(f"/api/v1/signatures/{signature.id}")

    assert get_response.status_code == 403
    assert delete_response.status_code == 403


@pytest.mark.anyio
async def test_team_member_can_get_and_delete_signature(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
):
    session = await _create_session(authenticated_client, "member")
    signature = await _create_signature(db_session, session["id"])

    get_response = await authenticated_client.get(f"/api/v1/signatures/session/{session['id']}")
    delete_response = await authenticated_client.delete(f"/api/v1/signatures/{signature.id}")
    get_after_delete_response = await authenticated_client.get(
        f"/api/v1/signatures/session/{session['id']}"
    )

    assert get_response.status_code == 200
    assert get_response.json()[0]["id"] == str(signature.id)
    assert delete_response.status_code == 204
    assert get_after_delete_response.status_code == 200
    assert get_after_delete_response.json() == []
