from httpx import AsyncClient


async def test_beauty_status_and_presets_are_public(client: AsyncClient):
    status_response = await client.get("/api/v1/beauty/status")
    presets_response = await client.get("/api/v1/beauty/presets")

    assert status_response.status_code == 200
    assert presets_response.status_code == 200


async def test_beauty_processing_requires_authentication(client: AsyncClient):
    preview_response = await client.post(
        "/api/v1/beauty/preview",
        files={"file": ("photo.jpg", b"image", "image/jpeg")},
    )
    detect_response = await client.post(
        "/api/v1/beauty/detect-face",
        files={"file": ("photo.jpg", b"image", "image/jpeg")},
    )
    apply_response = await client.post(
        "/api/v1/beauty/apply",
        json={"photo_id": "photo-1", "image_url": "https://example.test/photo.jpg"},
    )

    assert preview_response.status_code == 401
    assert detect_response.status_code == 401
    assert apply_response.status_code == 401


async def test_authenticated_beauty_processing_preserves_empty_file_validation(
    authenticated_client: AsyncClient,
):
    preview_response = await authenticated_client.post(
        "/api/v1/beauty/preview",
        files={"file": ("photo.jpg", b"", "image/jpeg")},
    )
    detect_response = await authenticated_client.post(
        "/api/v1/beauty/detect-face",
        files={"file": ("photo.jpg", b"", "image/jpeg")},
    )

    assert preview_response.status_code == 400
    assert detect_response.status_code == 400


async def test_beauty_apply_fails_when_task_queue_unavailable(
    authenticated_client: AsyncClient,
    monkeypatch,
):
    from app.tasks import beauty_tasks

    def fail_to_enqueue(*_args, **_kwargs):
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr(beauty_tasks.apply_beauty_task, "delay", fail_to_enqueue)

    response = await authenticated_client.post(
        "/api/v1/beauty/apply",
        json={"photo_id": "photo-1", "image_url": "https://example.test/photo.jpg"},
    )

    assert response.status_code == 503
    assert "task queue is unavailable" in response.text
