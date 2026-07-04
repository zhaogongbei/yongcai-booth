import pytest
from httpx import AsyncClient


def _custom_template_layers() -> dict:
    return {
        "id": "custom-with-background",
        "name": "Custom Background Template",
        "paperSize": {"width": 101.6, "height": 152.4},
        "resolution": 300,
        "orientation": "portrait",
        "background": {
            "type": "image",
            "value": "data:image/png;base64,iVBORw0KGgo=",
        },
        "elements": [
            {
                "id": "photo-1",
                "type": "photo",
                "x": 120,
                "y": 180,
                "width": 960,
                "height": 1200,
                "rotation": 0,
                "opacity": 1,
                "zIndex": 1,
                "locked": False,
                "visible": True,
                "props": {"photoNumber": 1, "cropMode": "fill", "borderRadius": 0},
            }
        ],
    }


@pytest.mark.anyio
async def test_create_custom_template_with_background(authenticated_client: AsyncClient):
    team_response = await authenticated_client.post(
        "/api/v1/teams",
        json={"name": "Template Save Team", "slug": "template-save-team"},
    )
    assert team_response.status_code == 201
    team_id = team_response.json()["id"]

    layers = _custom_template_layers()
    response = await authenticated_client.post(
        "/api/v1/templates",
        json={
            "team_id": team_id,
            "name": "Custom Background Template",
            "description": "Saved from template editor",
            "size": "101.6x152.4mm",
            "canvas_width": 1200,
            "canvas_height": 1800,
            "layers": layers,
            "is_public": False,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["layers"]["background"]["type"] == "image"
    assert body["layers"]["background"]["value"].startswith("data:image/png;base64,")

    list_response = await authenticated_client.get(
        "/api/v1/templates",
        params={"team_id": team_id},
    )
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == body["id"]


@pytest.mark.anyio
async def test_create_template_returns_400_for_invalid_layers(authenticated_client: AsyncClient):
    team_response = await authenticated_client.post(
        "/api/v1/teams",
        json={"name": "Invalid Template Team", "slug": "invalid-template-team"},
    )
    assert team_response.status_code == 201

    response = await authenticated_client.post(
        "/api/v1/templates",
        json={
            "team_id": team_response.json()["id"],
            "name": "Broken Template",
            "layers": {"background": {"type": "color", "value": "#ffffff"}},
            "is_public": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Invalid template structure"


@pytest.mark.anyio
async def test_create_template_requires_visible_photo_frame(authenticated_client: AsyncClient):
    team_response = await authenticated_client.post(
        "/api/v1/teams",
        json={"name": "No Photo Frame Team", "slug": "no-photo-frame-team"},
    )
    assert team_response.status_code == 201

    layers = _custom_template_layers()
    layers["elements"] = []
    response = await authenticated_client.post(
        "/api/v1/templates",
        json={
            "team_id": team_response.json()["id"],
            "name": "Background Only Template",
            "layers": layers,
            "is_public": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Invalid template structure"


@pytest.mark.anyio
async def test_create_template_rejects_invalid_photo_number(authenticated_client: AsyncClient):
    team_response = await authenticated_client.post(
        "/api/v1/teams",
        json={"name": "Invalid Photo Number Team", "slug": "invalid-photo-number-team"},
    )
    assert team_response.status_code == 201

    layers = _custom_template_layers()
    layers["elements"][0]["props"]["photoNumber"] = 99
    response = await authenticated_client.post(
        "/api/v1/templates",
        json={
            "team_id": team_response.json()["id"],
            "name": "Invalid Photo Number Template",
            "layers": layers,
            "is_public": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Invalid template structure"
