from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.tasks import photo_tasks


def _jpeg_bytes(color: str = "red") -> bytes:
    buf = BytesIO()
    Image.new("RGB", (24, 24), color).save(buf, format="JPEG")
    return buf.getvalue()


class FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


def _disable_r2(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(photo_tasks.settings, "R2_ACCESS_KEY_ID", "", raising=False)
    monkeypatch.setattr(photo_tasks.settings, "R2_SECRET_ACCESS_KEY", "", raising=False)


def test_process_photo_without_r2_writes_local_processed_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    _disable_r2(monkeypatch)
    monkeypatch.setattr(
        photo_tasks.requests,
        "get",
        lambda *_args, **_kwargs: FakeResponse(_jpeg_bytes("red")),
    )

    result = photo_tasks.process_photo(
        "https://example.test/photo.jpg",
        "photo-123",
        {"brightness": 1.1},
    )

    assert result["status"] == "completed"
    assert result["processed_url"] == "/uploads/photos/processed/processed_photo-123.jpg"
    assert (tmp_path / result["processed_url"].lstrip("/")).is_file()


def test_generate_collage_without_r2_writes_unique_local_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    _disable_r2(monkeypatch)
    monkeypatch.setattr(
        photo_tasks.requests,
        "get",
        lambda *_args, **_kwargs: FakeResponse(_jpeg_bytes("blue")),
    )

    result = photo_tasks.generate_collage(
        ["https://example.test/one.jpg", "https://example.test/two.jpg"],
    )

    assert result["status"] == "completed"
    assert result["collage_url"].startswith("/uploads/photos/collages/collage_")
    assert result["collage_url"].endswith(".jpg")
    assert (tmp_path / result["collage_url"].lstrip("/")).is_file()
