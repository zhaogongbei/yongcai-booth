from uuid import uuid4

import pytest
from httpx import AsyncClient


async def _create_event(client: AsyncClient, slug: str) -> dict:
    team_response = await client.post(
        "/api/v1/teams",
        json={"name": f"Config Team {slug}", "slug": f"config-team-{slug}"},
    )
    assert team_response.status_code == 201

    event_response = await client.post(
        "/api/v1/events",
        json={
            "name": f"Config Event {slug}",
            "team_id": team_response.json()["id"],
            "start_date": "2026-07-01T10:00:00Z",
            "end_date": "2026-07-01T18:00:00Z",
        },
    )
    assert event_response.status_code == 201
    return event_response.json()


@pytest.mark.anyio
async def test_survey_config_can_update_after_default_get(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "survey")

    get_response = await authenticated_client.get(f"/api/v1/surveys/event/{event['id']}")
    assert get_response.status_code == 200

    update_response = await authenticated_client.put(
        f"/api/v1/surveys/event/{event['id']}",
        json={
            "enabled": True,
            "title": "Visitor Feedback",
            "questions": [
                {
                    "id": "q1",
                    "type": "text_short",
                    "text": "How was the experience?",
                    "required": True,
                    "options": [],
                    "order": 0,
                }
            ],
        },
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["enabled"] is True
    assert data["title"] == "Visitor Feedback"
    assert data["questions"][0]["id"] == "q1"


@pytest.mark.anyio
async def test_disclaimer_config_can_update_after_default_get(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "disclaimer")

    get_response = await authenticated_client.get(f"/api/v1/disclaimers/event/{event['id']}")
    assert get_response.status_code == 200

    update_response = await authenticated_client.put(
        f"/api/v1/disclaimers/event/{event['id']}",
        json={
            "enabled": True,
            "title": "Event Terms",
            "text": "Please accept the event terms.",
            "require_signature": True,
        },
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["enabled"] is True
    assert data["title"] == "Event Terms"
    assert data["require_signature"] is True


@pytest.mark.anyio
async def test_survey_export_without_config_returns_404(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "survey-export-missing")

    response = await authenticated_client.get(f"/api/v1/surveys/responses/export/{event['id']}")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "该事件没有调查配置"


@pytest.mark.anyio
async def test_accepting_disclaimer_twice_returns_400(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "disclaimer-duplicate")
    get_response = await authenticated_client.get(f"/api/v1/disclaimers/event/{event['id']}")
    assert get_response.status_code == 200

    session_response = await authenticated_client.post(
        "/api/v1/photos/sessions",
        json={"event_id": event["id"]},
    )
    assert session_response.status_code == 201

    payload = {"event_id": event["id"], "session_id": session_response.json()["id"]}

    first_response = await authenticated_client.post("/api/v1/disclaimers/accept", json=payload)
    second_response = await authenticated_client.post("/api/v1/disclaimers/accept", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert second_response.json()["error"]["message"] == "已经接受过免责声明"


@pytest.mark.anyio
async def test_accepting_disclaimer_without_config_returns_404(
    authenticated_client: AsyncClient,
):
    event = await _create_event(authenticated_client, "disclaimer-missing")
    session_id = str(uuid4())

    response = await authenticated_client.post(
        "/api/v1/disclaimers/accept",
        json={"event_id": event["id"], "session_id": session_id},
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "免责声明不存在"
