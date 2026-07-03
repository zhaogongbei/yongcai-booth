import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_upload_prop_rejects_non_png_with_400(authenticated_client: AsyncClient):
    create_response = await authenticated_client.post(
        "/api/v1/teams",
        json={"name": "Props Team", "slug": "props-team"},
    )
    team_id = create_response.json()["id"]

    response = await authenticated_client.post(
        "/api/v1/props",
        headers={"X-Team-Id": team_id},
        params={
            "name": "Not A PNG",
            "category": "自定义",
        },
        files={"file": ("prop.jpg", b"not-a-png", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Only PNG files are allowed"
