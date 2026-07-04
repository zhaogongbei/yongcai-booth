from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

PLAYLIST_PAYLOAD = {
    "items": [
        {
            "timing": "attract_screen",
            "enabled": True,
            "text": "Welcome to the booth",
            "language": "en-US",
            "voice": "female",
        }
    ]
}


async def _create_event(client: AsyncClient, slug: str) -> dict:
    team_response = await client.post(
        "/api/v1/teams",
        json={"name": f"Virtual Attendant Team {slug}", "slug": f"virtual-attendant-{slug}"},
    )
    assert team_response.status_code == 201

    event_response = await client.post(
        "/api/v1/events",
        json={
            "name": f"Virtual Attendant Event {slug}",
            "team_id": team_response.json()["id"],
            "start_date": "2026-07-01T10:00:00Z",
            "end_date": "2026-07-01T18:00:00Z",
        },
    )
    assert event_response.status_code == 201
    return event_response.json()


async def _other_client(authenticated_client: AsyncClient, slug: str) -> AsyncClient:
    other_user_data = {
        "email": f"virtual-attendant-other-{slug}@example.com",
        "password": "OtherPass123!@",
        "full_name": "Virtual Attendant Other",
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
async def test_get_playlist_remains_public(client: AsyncClient):
    response = await client.get(f"/api/v1/virtual-attendant/playlist/{uuid4()}")

    assert response.status_code == 200
    assert len(response.json()) > 0


@pytest.mark.anyio
async def test_update_playlist_requires_authentication(client: AsyncClient):
    response = await client.put(
        f"/api/v1/virtual-attendant/playlist/{uuid4()}",
        json=PLAYLIST_PAYLOAD,
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_update_playlist_returns_404_for_missing_event(
    authenticated_client: AsyncClient,
):
    response = await authenticated_client.put(
        f"/api/v1/virtual-attendant/playlist/{uuid4()}",
        json=PLAYLIST_PAYLOAD,
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Event not found"


@pytest.mark.anyio
async def test_update_playlist_rejects_non_member(authenticated_client: AsyncClient):
    event = await _create_event(authenticated_client, "non-member")

    async with await _other_client(authenticated_client, "non-member") as other_client:
        response = await other_client.put(
            f"/api/v1/virtual-attendant/playlist/{event['id']}",
            json=PLAYLIST_PAYLOAD,
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_update_playlist_allows_team_member(authenticated_client: AsyncClient):
    event = await _create_event(authenticated_client, "member")

    response = await authenticated_client.put(
        f"/api/v1/virtual-attendant/playlist/{event['id']}",
        json=PLAYLIST_PAYLOAD,
    )
    public_response = await authenticated_client.get(
        f"/api/v1/virtual-attendant/playlist/{event['id']}"
    )

    assert response.status_code == 200
    assert response.json() == PLAYLIST_PAYLOAD["items"]
    assert public_response.status_code == 200
    assert public_response.json() == PLAYLIST_PAYLOAD["items"]


@pytest.mark.anyio
async def test_preview_tts_requires_authentication(client: AsyncClient):
    response = await client.post(
        "/api/v1/virtual-attendant/preview",
        json={"text": "Hello", "language": "en-US", "voice": "female"},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_preview_tts_allows_authenticated_user(
    authenticated_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_synthesize(text: str, language: str, voice: str) -> bytes:
        return b"mp3"

    monkeypatch.setattr(
        "app.api.v1.virtual_attendant.TTSService.synthesize",
        fake_synthesize,
    )

    response = await authenticated_client.post(
        "/api/v1/virtual-attendant/preview",
        json={"text": "Hello", "language": "en-US", "voice": "female"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"mp3"
