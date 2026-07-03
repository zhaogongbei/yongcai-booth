import io
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image

from app.api.v1.green_screen import _delete_local_green_screen_file


def _png_bytes(color: tuple[int, int, int] = (0, 255, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color=color).save(buf, format="PNG")
    return buf.getvalue()


async def _create_event(client: AsyncClient, slug: str) -> dict:
    team_response = await client.post(
        "/api/v1/teams",
        json={"name": f"Green Screen Team {slug}", "slug": f"green-screen-team-{slug}"},
    )
    assert team_response.status_code == 201

    event_response = await client.post(
        "/api/v1/events",
        json={
            "name": f"Green Screen Event {slug}",
            "team_id": team_response.json()["id"],
            "start_date": "2026-07-01T10:00:00Z",
            "end_date": "2026-07-01T18:00:00Z",
        },
    )
    assert event_response.status_code == 201
    return event_response.json()


@pytest.mark.anyio
async def test_upload_background_saves_local_files(
    authenticated_client: AsyncClient,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    event = await _create_event(authenticated_client, "upload")
    event_id = event["id"]

    response = await authenticated_client.post(
        "/api/v1/green-screen/backgrounds",
        data={
            "event_id": event_id,
            "name": "Stage Backdrop",
        },
        files={
            "file": ("background.png", _png_bytes(), "image/png"),
            "overlay_file": ("overlay.png", _png_bytes((255, 255, 255)), "image/png"),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Stage Backdrop"
    assert data["background_url"].startswith(
        f"/api/v1/green-screen/assets/{event_id}/backgrounds/"
    )
    assert data["overlay_url"].startswith(f"/api/v1/green-screen/assets/{event_id}/overlays/")

    background_filename = data["background_url"].rsplit("/", 1)[-1]
    overlay_filename = data["overlay_url"].rsplit("/", 1)[-1]
    assert (
        tmp_path / "uploads" / "green-screen" / event_id / "backgrounds" / background_filename
    ).is_file()
    assert (
        tmp_path / "uploads" / "green-screen" / event_id / "overlays" / overlay_filename
    ).is_file()

    asset_response = await authenticated_client.get(data["background_url"])
    assert asset_response.status_code == 200
    assert asset_response.content == _png_bytes()

    settings_response = await authenticated_client.get(f"/api/v1/green-screen/settings/{event_id}")
    assert settings_response.status_code == 200
    settings = settings_response.json()
    assert settings["backgrounds"][0]["id"] == data["id"]
    assert settings["backgrounds"][0]["background_url"] == data["background_url"]


@pytest.mark.anyio
async def test_upload_background_rejects_empty_file(client: AsyncClient):
    response = await client.post(
        "/api/v1/green-screen/backgrounds",
        data={
            "event_id": str(uuid4()),
            "name": "Empty Backdrop",
        },
        files={"file": ("empty.png", b"", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Background file is empty"


@pytest.mark.anyio
async def test_get_green_screen_settings_returns_404_for_missing_event(client: AsyncClient):
    response = await client.get(f"/api/v1/green-screen/settings/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Event not found"


@pytest.mark.anyio
async def test_analyze_test_photo_rejects_empty_file_with_400(client: AsyncClient):
    response = await client.post(
        "/api/v1/green-screen/test-photo",
        files={"file": ("empty.png", b"", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Image file is empty"


@pytest.mark.anyio
async def test_delete_background_removes_persisted_background(
    authenticated_client: AsyncClient,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    event = await _create_event(authenticated_client, "delete")
    event_id = event["id"]

    upload_response = await authenticated_client.post(
        "/api/v1/green-screen/backgrounds",
        data={
            "event_id": event_id,
            "name": "Deletable Backdrop",
        },
        files={"file": ("background.png", _png_bytes(), "image/png")},
    )
    assert upload_response.status_code == 200
    background = upload_response.json()
    background_filename = background["background_url"].rsplit("/", 1)[-1]
    background_path = (
        tmp_path / "uploads" / "green-screen" / event_id / "backgrounds" / background_filename
    )
    assert background_path.is_file()

    response = await authenticated_client.delete(
        f"/api/v1/green-screen/backgrounds/{background['id']}",
        params={"event_id": event_id},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert not background_path.exists()

    settings_response = await authenticated_client.get(
        f"/api/v1/green-screen/settings/{event_id}"
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["backgrounds"] == []


def test_delete_local_green_screen_file_rejects_sibling_uploads_prefix(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "uploads" / "green-screen").mkdir(parents=True)
    sibling = tmp_path / "uploads_evil"
    sibling.mkdir()
    secret = sibling / "secret.png"
    secret.write_bytes(b"secret")

    _delete_local_green_screen_file("/uploads/green-screen/../../uploads_evil/secret.png")

    assert secret.is_file()


@pytest.mark.anyio
async def test_process_photos_reports_not_implemented(client: AsyncClient):
    response = await client.post(
        "/api/v1/green-screen/process",
        params={
            "event_id": str(uuid4()),
        },
        json={
            "request": {
                "settings": {
                    "enabled": True,
                    "mode": "auto",
                    "color_to_remove": "#00FF00",
                    "sensitivity": 50,
                    "smoothness": 30,
                    "use_flash": False,
                    "background_mode": "rotate",
                    "output_size": "template",
                    "current_background_index": 0,
                },
                "apply_to_all": False,
            },
            "photo_ids": [str(uuid4())],
        },
    )

    assert response.status_code == 501
    assert response.json()["error"]["message"] == (
        "Batch green screen processing is not implemented"
    )


@pytest.mark.anyio
async def test_update_green_screen_settings_persists(authenticated_client: AsyncClient):
    event = await _create_event(authenticated_client, "settings")
    event_id = event["id"]

    response = await authenticated_client.put(
        f"/api/v1/green-screen/settings/{event_id}",
        json={
            "enabled": True,
            "mode": "auto",
            "color_to_remove": "#00FF00",
            "sensitivity": 50,
            "smoothness": 30,
            "use_flash": False,
            "background_mode": "rotate",
            "output_size": "template",
            "current_background_index": 0,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["sensitivity"] == 50
    assert data["background_mode"] == "rotate"

    get_response = await authenticated_client.get(f"/api/v1/green-screen/settings/{event_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == data["id"]
    assert get_response.json()["enabled"] is True
