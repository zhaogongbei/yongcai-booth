from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_upload_signature_rejects_non_png_with_400(client: AsyncClient):
    response = await client.post(
        f"/api/v1/signatures?session_id={uuid4()}",
        files={"signature_file": ("signature.jpg", b"not a png", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "仅支持PNG格式的签名"
