import io
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app


async def _create_event(client: AsyncClient, slug: str) -> dict:
    team_response = await client.post(
        "/api/v1/teams",
        json={"name": f"Team {slug}", "slug": f"team-{slug}"},
    )
    assert team_response.status_code == 201

    event_response = await client.post(
        "/api/v1/events",
        json={
            "name": f"Event {slug}",
            "team_id": team_response.json()["id"],
            "start_date": "2026-07-01T10:00:00Z",
            "end_date": "2026-07-01T18:00:00Z",
        },
    )
    assert event_response.status_code == 201
    return event_response.json()


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 24), color=(80, 120, 180)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.anyio
async def test_create_list_and_complete_photo_session(authenticated_client: AsyncClient):
    event = await _create_event(authenticated_client, "sessions")

    create_response = await authenticated_client.post(
        "/api/v1/photos/sessions",
        json={"event_id": event["id"], "email": "guest@example.com"},
    )
    assert create_response.status_code == 201
    session = create_response.json()
    assert session["event_id"] == event["id"]
    assert session["completed_at"] is None

    list_response = await authenticated_client.get(
        "/api/v1/photos/sessions",
        params={"event_id": event["id"]},
    )
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [session["id"]]

    complete_response = await authenticated_client.post(
        f"/api/v1/photos/sessions/{session['id']}/complete"
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["completed_at"] is not None


@pytest.mark.anyio
async def test_non_member_cannot_create_photo_session(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "session-owner")

    other_user = {
        "email": "photo-session-other@example.com",
        "password": "OtherPass123!@",
        "full_name": "Other User",
    }
    await authenticated_client.post("/api/v1/auth/register", json=other_user)
    login_response = await authenticated_client.post(
        "/api/v1/auth/login",
        data={"username": other_user["email"], "password": other_user["password"]},
    )
    token = login_response.json()["access_token"]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as other_client:
        response = await other_client.post(
            "/api/v1/photos/sessions",
            json={"event_id": event["id"]},
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_upload_rejects_session_from_another_event(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    event_one = await _create_event(authenticated_client, "upload-one")
    event_two = await _create_event(authenticated_client, "upload-two")

    session_response = await authenticated_client.post(
        "/api/v1/photos/sessions",
        json={"event_id": event_two["id"]},
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["id"]

    response = await authenticated_client.post(
        "/api/v1/photos/upload",
        params={"event_id": event_one["id"], "session_id": session_id},
        files={"file": ("capture.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 400
    assert "session" in response.json()["error"]["message"].lower()
    assert not (tmp_path / "uploads").exists()


@pytest.mark.anyio
async def test_upload_saves_local_original_and_thumbnail(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    event = await _create_event(authenticated_client, "local-upload")
    session_response = await authenticated_client.post(
        "/api/v1/photos/sessions",
        json={"event_id": event["id"]},
    )
    assert session_response.status_code == 201

    response = await authenticated_client.post(
        "/api/v1/photos/upload",
        params={"event_id": event["id"], "session_id": session_response.json()["id"]},
        files={"file": ("capture.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 201
    photo = response.json()
    assert photo["session_id"] == session_response.json()["id"]
    assert photo["original_url"].startswith("/uploads/photos/")
    assert photo["thumbnail_url"].startswith("/uploads/thumbnails/")
    assert photo["width"] == 32
    assert photo["height"] == 24

    assert (tmp_path / photo["original_url"].lstrip("/")).is_file()
    assert (tmp_path / photo["thumbnail_url"].lstrip("/")).is_file()
