import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from PIL import Image

from app.api.v1 import camera as camera_api


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
    Image.new("RGB", (40, 30), color=(120, 80, 160)).save(buf, format="JPEG")
    return buf.getvalue()


class FakeDslrController:
    def get_status(self):
        return {"connected": True, "controller_type": "gphoto2", "model": "Test DSLR"}

    async def capture(self) -> bytes:
        return _jpeg_bytes()

    async def get_settings(self):
        return {"iso": 800, "shutter_speed": "1/125"}


@pytest.mark.anyio
async def test_dslr_capture_with_event_creates_printable_photo(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(camera_api, "_get_controller", lambda: FakeDslrController())
    event = await _create_event(authenticated_client, "dslr-capture")
    session_response = await authenticated_client.post(
        "/api/v1/photos/sessions",
        json={"event_id": event["id"]},
    )
    assert session_response.status_code == 201

    response = await authenticated_client.post(
        "/api/v1/camera/capture",
        params={"event_id": event["id"], "session_id": session_response.json()["id"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["capture_method"] == "dslr"
    assert body["photo"]["event_id"] == event["id"]
    assert body["photo"]["session_id"] == session_response.json()["id"]
    assert body["photo"]["original_url"].startswith("/uploads/photos/")
    assert (tmp_path / body["photo"]["original_url"].lstrip("/")).is_file()
