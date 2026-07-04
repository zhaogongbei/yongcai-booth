from pathlib import Path

import pytest
from httpx import AsyncClient

from app.api.v1 import gopro as gopro_api


class FakeGoProController:
    @property
    def is_connected(self) -> bool:
        return True

    async def take_photo(self) -> bytes:
        return b"fake-jpeg"

    async def stop_recording(self) -> bytes:
        return b"fake-mp4"


@pytest.mark.anyio
async def test_gopro_photo_returns_readable_media_url(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gopro_api, "gopro_controller", FakeGoProController())

    response = await authenticated_client.post("/api/v1/gopro/photo")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["temp_url"].startswith("/api/v1/media/gopro/gopro_")

    media_response = await authenticated_client.get(body["temp_url"])
    assert media_response.status_code == 200
    assert media_response.content == b"fake-jpeg"


@pytest.mark.anyio
async def test_gopro_video_returns_readable_media_url(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gopro_api, "gopro_controller", FakeGoProController())

    response = await authenticated_client.post("/api/v1/gopro/record/stop")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["temp_url"].startswith("/api/v1/media/gopro/gopro_")

    media_response = await authenticated_client.get(body["temp_url"])
    assert media_response.status_code == 200
    assert media_response.content == b"fake-mp4"
