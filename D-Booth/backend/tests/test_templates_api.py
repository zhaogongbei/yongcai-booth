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


@pytest.mark.anyio
async def test_template_catalog_is_public_and_team_lists_remain_isolated(
    authenticated_client: AsyncClient,
):
    primary_authorization = authenticated_client.headers["Authorization"]

    primary_team_response = await authenticated_client.post(
        "/api/v1/teams",
        json={"name": "Primary Catalog Team", "slug": "primary-catalog-team"},
    )
    assert primary_team_response.status_code == 201
    primary_team_id = primary_team_response.json()["id"]

    primary_private_response = await authenticated_client.post(
        "/api/v1/templates",
        json={
            "team_id": primary_team_id,
            "name": "Primary Private Template",
            "layers": _custom_template_layers(),
            "is_public": False,
        },
    )
    assert primary_private_response.status_code == 201

    primary_public_response = await authenticated_client.post(
        "/api/v1/templates",
        json={
            "team_id": primary_team_id,
            "name": "Primary Public Template",
            "layers": _custom_template_layers(),
            "is_public": True,
        },
    )
    assert primary_public_response.status_code == 201

    second_user = {
        "email": "catalog-owner@example.com",
        "password": "CatalogPass123!@",
        "full_name": "Catalog Owner",
    }
    register_response = await authenticated_client.post("/api/v1/auth/register", json=second_user)
    assert register_response.status_code == 201
    login_response = await authenticated_client.post(
        "/api/v1/auth/login",
        data={"username": second_user["email"], "password": second_user["password"]},
    )
    assert login_response.status_code == 200
    authenticated_client.headers["Authorization"] = (
        f"Bearer {login_response.json()['access_token']}"
    )

    second_team_response = await authenticated_client.post(
        "/api/v1/teams",
        json={"name": "Second Catalog Team", "slug": "second-catalog-team"},
    )
    assert second_team_response.status_code == 201
    second_team_id = second_team_response.json()["id"]

    second_public_response = await authenticated_client.post(
        "/api/v1/templates",
        json={
            "team_id": second_team_id,
            "name": "Second Public Template",
            "layers": _custom_template_layers(),
            "is_public": True,
        },
    )
    assert second_public_response.status_code == 201

    second_private_response = await authenticated_client.post(
        "/api/v1/templates",
        json={
            "team_id": second_team_id,
            "name": "Second Private Template",
            "layers": _custom_template_layers(),
            "is_public": False,
        },
    )
    assert second_private_response.status_code == 201

    authenticated_client.headers["Authorization"] = primary_authorization

    team_list_response = await authenticated_client.get(
        "/api/v1/templates",
        params={"team_id": primary_team_id},
    )
    assert team_list_response.status_code == 200
    assert {item["name"] for item in team_list_response.json()} == {
        "Primary Private Template",
        "Primary Public Template",
    }

    public_team_list_response = await authenticated_client.get(
        "/api/v1/templates",
        params={"team_id": primary_team_id, "is_public": True},
    )
    assert public_team_list_response.status_code == 200
    assert [item["name"] for item in public_team_list_response.json()] == [
        "Primary Public Template"
    ]

    catalog_response = await authenticated_client.get("/api/v1/templates/catalog")
    assert catalog_response.status_code == 200
    catalog = catalog_response.json()
    assert {item["name"] for item in catalog} == {
        "Primary Public Template",
        "Second Public Template",
    }
    assert all("team_id" not in item for item in catalog)
    assert all("is_public" not in item for item in catalog)
