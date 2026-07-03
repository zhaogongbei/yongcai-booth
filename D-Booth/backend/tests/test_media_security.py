import pytest
from fastapi import HTTPException

from app.api.v1.media import serve_media


@pytest.mark.anyio
async def test_serve_media_rejects_sibling_uploads_prefix(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "uploads").mkdir()
    sibling = tmp_path / "uploads_evil"
    sibling.mkdir()
    (sibling / "secret.txt").write_text("secret", encoding="utf-8")

    with pytest.raises(HTTPException) as exc:
        await serve_media("../uploads_evil/secret.txt", current_user=object())

    assert exc.value.status_code == 403
