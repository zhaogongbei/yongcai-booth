import io
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image


def _png_bytes(color: tuple[int, int, int] = (0, 255, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color=color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.anyio
async def test_upload_background_saves_local_files(
    client: AsyncClient,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    event_id = uuid4()

    response = await client.post(
        "/api/v1/green-screen/backgrounds",
        data={
            "event_id": str(event_id),
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
    assert data["background_url"].startswith(f"/uploads/green-screen/{event_id}/backgrounds/")
    assert data["overlay_url"].startswith(f"/uploads/green-screen/{event_id}/overlays/")
    assert (tmp_path / data["background_url"].lstrip("/")).is_file()
    assert (tmp_path / data["overlay_url"].lstrip("/")).is_file()


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
async def test_delete_background_reports_not_implemented(client: AsyncClient):
    response = await client.delete(
        f"/api/v1/green-screen/backgrounds/{uuid4()}",
        params={"event_id": str(uuid4())},
    )

    assert response.status_code == 501
    assert response.json()["error"]["message"] == (
        "Green screen background deletion is not implemented"
    )


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
