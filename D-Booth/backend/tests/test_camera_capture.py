import io
from pathlib import Path

import pytest
from httpx import AsyncClient
from PIL import Image

from app.api.v1 import camera as camera_api
from app.services.camera_service import GPhoto2CameraController, WebcamCameraController


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


class EmptyDslrController(FakeDslrController):
    async def capture(self) -> bytes:
        return b""


@pytest.mark.anyio
async def test_gphoto2_settings_do_not_return_simulated_exposure_values():
    controller = GPhoto2CameraController()
    controller._connected = True

    settings = await controller.get_settings()

    assert settings["settings_available"] is False
    assert settings["settings_writable"] is True
    assert settings["source"] == "gphoto2"
    assert "iso" not in settings
    assert "shutter_speed" not in settings


@pytest.mark.anyio
async def test_webcam_settings_are_explicitly_unavailable():
    controller = WebcamCameraController()

    settings = await controller.get_settings()

    assert settings["settings_available"] is False
    assert settings["settings_writable"] is False
    assert settings["source"] == "webcam"
    assert "iso" not in settings
    with pytest.raises(NotImplementedError, match="不支持后端设置"):
        await controller.set_setting("iso", 400)


@pytest.mark.anyio
async def test_webcam_setting_update_fails_closed(
    authenticated_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(camera_api, "_get_controller", WebcamCameraController)

    response = await authenticated_client.put(
        "/api/v1/camera/settings",
        json={"iso": 400},
    )

    assert response.status_code == 501
    assert response.json()["error"]["message"] == "浏览器摄像头曝光参数不支持后端设置"


@pytest.mark.anyio
async def test_empty_dslr_capture_returns_controlled_server_error(
    authenticated_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(camera_api, "_get_controller", EmptyDslrController)

    response = await authenticated_client.post("/api/v1/camera/capture")

    assert response.status_code == 500
    assert response.json()["error"]["message"] == "相机拍摄失败，未获取到图像数据"


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
